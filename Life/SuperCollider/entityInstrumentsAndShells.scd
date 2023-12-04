(
// GLOBAL VARS
~reverbFFTsize = 4096;
~reverbIR = "Audio/ConcertHallIR.wav";
s.options.memSize = 2.pow(15);


~setUpGroups = {
	~sources = Group.new;
	~reverb = Group.after(~sources);
	~reverbBus = Bus.audio(s, 2);
};


~setUpReverbAndDistance = {
	~distance = {
		|inUGen, distance, directOut=0, reverbOut=0|
		var lpffedUp = LPF.ar(inUGen, distance.linexp(0, 1, 15000, 400));
		var lowPassProportion = distance.linlin(0, 0.5, 0, 1);
		var proportionallyLowPassed = (inUGen * (1 - lowPassProportion)) + (lpffedUp * lowPassProportion);
		var directProportion = distance.linlin(0, 1, 1, 0.2);
		var verbedProportion = distance.linlin(0, 1, 0.2, 1);
		Out.ar(directOut, proportionallyLowPassed * directProportion);
		Out.ar(reverbOut, proportionallyLowPassed * verbedProportion);
	};


	{ // load irs and start the reverb
		var irbuffers, bufsizes;
		irbuffers = Array.fill(2, { |i|
			Buffer.readChannel(s, ~reverbIR.resolveRelative, channels:[i]);
		});
		s.sync;

		bufsizes = Array.fill(2, { |i|
			PartConv.calcBufSize(~reverbFFTsize, irbuffers[i]);
		});


		~irspectrums = Array.fill(2, { |i|
			var spec = Buffer.alloc(s, bufsizes[i], 1);
			spec.preparePartConv(irbuffers[i], ~reverbFFTsize);
			spec;
		});
		s.sync;

		SynthDef(\verb, {
			arg out=0;
			var signalIn = In.ar(~reverbBus, 2);
			Out.ar(out, PartConv.ar(signalIn, ~reverbFFTsize, ~irspectrums, 0.05));
		}).play(target:~reverb);
	}.fork;
};

~setUpInstruments = {
	~resetFirstTimeDifferent = {
		/* A function that sends (reset) impulses at regular intervals, allowing the first interval to be different from the others
		Takes a rate argument that can be continuously variable */
		arg firstResetDur, subsequentResetDur, rate=1;
		var initialImpulsePhase = 1 - (firstResetDur.mod(subsequentResetDur) / subsequentResetDur);
		(Sweep.ar(rate:rate) > firstResetDur) * Impulse.ar(rate/subsequentResetDur, phase:initialImpulsePhase);
	};

	~introLoopBufPhasor = {
		/* A function that returns a phasor for reading into a buffer. The phasor loops between loopStart and loopEnd, but can start either within
		that range or before that range (cases which have to be handled differently). Arguments are in seconds and translated to the sample rate of
		the buffer.Takes a rate argument that can be continuously variable. */
		arg buf, start, loopStart, loopEnd, rate=1;
		var resetTrigger = ~resetFirstTimeDifferent.value(loopEnd - start, loopEnd - loopStart, rate:rate);
		(start < loopStart).if({
			Phasor.ar(
				resetTrigger, BufRateScale.ir(buf) * rate, BufSampleRate.ir(buf) * start, inf, BufSampleRate.ir(buf) * loopStart
			);
		}, {
			Phasor.ar(
				Impulse.ar(0), rate, BufSampleRate.ir(buf) * loopStart, BufSampleRate.ir(buf) * loopEnd, BufSampleRate.ir(buf) * start
			);
		});
	};

	~fadeCycle = {
		/* Given start, loopStart, loopEnd, fadeLength, creates an envelope for crossfading back and forth between two looping copies of the sound
		source. Crucially, it can read into this envelope at any value t, which means that it can be used with continously varying rate */
		arg t, start, loopStart, loopEnd, fadeLength;
		var cycleStart = loopEnd - start - fadeLength;
		var loopLength = loopEnd - loopStart;
		var flatLength = loopLength - (2 * fadeLength);
		var cycleLength = 2 * (flatLength + fadeLength);
		var tCycle = (t - cycleStart).mod(cycleLength);
		// An unfortunately complicated way of figuring out which segment of the envelope we are in·
		var whichCase = 1;
		whichCase = Select.kr((fadeLength <= tCycle) * (tCycle < (fadeLength + flatLength)), [whichCase, 2]);
		whichCase = Select.kr(((fadeLength + flatLength) <= tCycle) * (tCycle < ((2 * fadeLength) + flatLength)), [whichCase, 3]);
		whichCase = Select.kr(tCycle >= ((2 * fadeLength) + flatLength), [whichCase, 4]);
		whichCase = Select.kr(t < cycleStart, [whichCase, 0]);
		Select.ar(whichCase, [
			DC.ar(0),  // inital play through (first voice)
			tCycle / fadeLength, // crossfade to second voice
			DC.ar(1),  // second voice
			1 - ((tCycle - fadeLength - flatLength) / fadeLength), // crossfade to first voice
			DC.ar(0) // first voice
		]);
	};

	~loopSound = {
		/* The main function that loops and crossfades a given buffer, putting together all of the elements above. */
		arg buf=0
		,freq=440
		,volume=1
		,start=0
		,loopStart=1
		,loopEnd=3.5 // between 0 (min) and 1 (max)
		,fadeTime=0.5
		,gate=1
		,attack=0.01
		,sustain=1
		,release=0.2
		,f0=440
		,pan=0.2;

		var rate = freq / f0;
		var loopDur = loopEnd - loopStart;
		var phaseA = ~introLoopBufPhasor.value(buf, start, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * start).min(BufSampleRate.ir(buf) * loopEnd);
		var phaseB = ~introLoopBufPhasor.value(buf, loopStart + fadeTime - loopEnd, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * loopStart).min(BufSampleRate.ir(buf) * loopEnd);
		var whichPhase = ~fadeCycle.value(Sweep.ar(rate:rate), start, loopStart, loopEnd, fadeTime);
		var out = SelectX.ar(whichPhase, [BufRd.ar(1, buf, phaseA), BufRd.ar(1, buf, phaseB)]);
		var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, 1, doneAction:2);
		out * env * volume;
	};

	~oneShot = {
		arg buf=0
		,freq=220
		,volume=1
		,gate=1
		,f0=63.8.midicps
		,pan=0.2;
		var out = PlayBuf.ar(1, buf, BufRateScale.kr(buf) * freq / f0, doneAction: Done.freeSelf);
		var env = EnvGate(1, gate, 0.1);
		out * env * volume;
	};

	~bambooBuf = Buffer.read(s, "Audio/BambooFlute.wav".resolveRelative);
	~ocarinaBuf = Buffer.read(s, "Audio/Ocarina.wav".resolveRelative);
	~beeBuf = Buffer.read(s, "Audio/BeeWithAttack.wav".resolveRelative);
	~highPluckBuf = Buffer.read(s, "Audio/HighPluck.wav".resolveRelative);
	~woodTapBuf = Buffer.read(s, "Audio/WoodTap.wav".resolveRelative);
	~whaleBuf = Buffer.read(s, "Audio/Whale3.wav".resolveRelative);
	~cricketBuf = Buffer.read(s, "Audio/Cricket.wav".resolveRelative);
	s.sync;
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\bamboo, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5) * 0.3,
				gate: gate,
				buf:~bambooBuf,
				f0:198,
				loopStart:0.6,
				loopEnd:3.6, // between 0 (min) and 1 (max)
				fadeTime:0.5,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\ocarina, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~loopSound.value(
				freq: Lag.kr(freq, 1.2),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				buf:~ocarinaBuf,
				f0:51.8.midicps,
				loopStart:1,
				loopEnd:19, // between 0 (min) and 1 (max)
				fadeTime:1.0,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		});
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\whale, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				buf:~whaleBuf,
				f0:316,
				loopStart:1.6,
				loopEnd:3.3, // between 0 (min) and 1 (max)
				fadeTime:0.3,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\cricket, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				buf:~cricketBuf,
				f0:2798,
				loopStart:0.313,
				loopEnd:1.815, // between 0 (min) and 1 (max)
				fadeTime:0.05,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\bee, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.2) * 1.4,
				gate: gate,
				buf:~beeBuf,
				f0:274,
				loopStart:1,
				loopEnd:3, // between 0 (min) and 1 (max)
				fadeTime:0.6,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		}).add;
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\highPluck, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~oneShot.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				buf:~highPluckBuf,
				f0:1595,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\woodTap, {
			arg freq, volume=1, gate=1, pan=0.5, dist=0;
			var instSound = ~oneShot.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5) * 0.35,
				gate: gate,
				buf:~woodTapBuf,
				f0:1601,
			);
			~distance.value(Pan2.ar(instSound, Lag.kr(pan, 1).linlin(0, 1, -1, 1)), Lag.kr(dist, 1), 0, ~reverbBus);
		})
	);
	// s.sync;
	// x = Synth(\bamboo, [\freq, 440, \pan, 0.8]);
};

~setUpShells = {
	var winenv = Env([1, 0], [1.0], [-3]);
	var panChannels = 10;

	~shellSoundBuf = Buffer.read(s, "Audio/shellsCompressedFiltered.wav".resolveRelative);
	// a custom envelope
	~grainWindowBuf = Buffer.sendCollection(s, winenv.discretize, 1);

	SynthDef(\shellGrains, { |out=0, gate = 1, volume = 1|
		var panIndex, pan, filter, trig, env, granulated;
		var activity = NamedControl.kr(\activities, Array.fill(panChannels, {0}));  // distribution of activity from left to right
		var averageHeights = NamedControl.kr(\averageHeights, Array.fill(panChannels, {0.5}));
		var activityPercent = activity.sum / panChannels;
		trig = Impulse.kr(activityPercent.explin(0.01, 1, 3, 100));
		panIndex = TWindex.kr(trig, activity, normalize: 1);
		pan = Select.kr(panIndex, Array.fill(panChannels, {|i| i.linlin(0, panChannels - 1, -1, 1)}));
		filter = Select.kr(panIndex, averageHeights);
		granulated = GrainBuf.ar(
			2, trig, 0.25, ~shellSoundBuf, filter.linexp(0, 1, 0.6, 1.5), WhiteNoise.kr(mul:0.2, add:filter*0.8 + 0.1), 2,
			pan,
			~grainWindowBuf);

		~distance.value(granulated * EnvFollow.ar(K2A.ar(Select.kr(panIndex, activity).linlin(0, 1, 0, 4))) * EnvGate(volume, gate), 0.2, out, ~reverbBus);
	}).add;

	OSCFunc.newMatching({|msg, time, addr, recvPort| x = Synth(\shellGrains)}, '/shells/start');
	OSCFunc.newMatching({|msg, time, addr, recvPort| x.setn(\activities, msg[1..])}, '/shells/activity');
	OSCFunc.newMatching({|msg, time, addr, recvPort| x.setn(\averageHeights, msg[1..])}, '/shells/heights');
	OSCFunc.newMatching({|msg, time, addr, recvPort| x.set(\gate, 0)}, '/shells/stop');
};

s.reboot;
s.waitForBoot({
	{
		MarcUtilities.setOutputLimiter;
		"Setting up groups...".post;
		~setUpGroups.value;	s.sync;
		"done.".postln;
		"Setting up reverb/distance function...".post;
		~setUpReverbAndDistance.value; s.sync;
		"done.".postln;
		"Setting up shells...".post;
		~setUpShells.value; s.sync;
		"done.".postln;
		"Setting up entity instruments...".post;
		~setUpInstruments.value; s.sync;
		"done.".postln;
	}.fork;
});
)


/*x = Synth(\bamboo, [\freq, 440, \pan, 0.8]);
x.set(\pan, 0.5)
x.set(\dist, 0.5)*/