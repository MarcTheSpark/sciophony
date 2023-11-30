(
{
	~loopSound = {
		arg buf=0
		,freq=220
		,volume=1
		,startTime=0
		,loopStartTime=1.2
		,loopEndTime=3 // between 0 (min) and 1 (max)
		,fadeTime=0.01
		,gate=1
		,attack=0.01
		,sustain=1
		,release=0.2
		,f0=63.8.midicps
		,pan=0.2;

		var rate = freq / f0;
		var fadeFrames = fadeTime * BufSampleRate.kr(buf);
		var sampleStart = BufSampleRate.kr(buf) * startTime;
		var loopStart = BufSampleRate.kr(buf) * loopStartTime;
		var loopEnd = BufSampleRate.kr(buf) * loopEndTime;
		var loopFrames = loopEnd - loopStart + 1;
		var playSR = rate * BufSampleRate.kr(buf);
		var loopTime = (loopFrames - fadeFrames)/playSR;
		var startUpTime = (loopStart - sampleStart)/playSR;

		var trigLoop = TDuty.ar(Dseq([startUpTime + loopTime, Dseq([loopTime], inf)]), gapFirst:1);

		var phaseA = Phasor.ar(trigLoop, rate, sampleStart, inf, loopStart);
		var phaseB = Phasor.ar(trigLoop, rate, loopEnd - fadeFrames, inf, loopEnd - fadeFrames);

		var srcA = BufRd.ar(buf.numChannels, buf, phaseA);
		var srcB = BufRd.ar(buf.numChannels, buf, phaseB);

		var startLoop = SetResetFF.ar(trigLoop);
		var loopPan = Phasor.ar(trigLoop, 2/fadeFrames * rate, -1, inf, -1).clip(-1,1);

		var out = Select.ar(startLoop, [srcA, LinXFade2.ar(srcB, srcA, pan:loopPan)]);
		var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, volume, doneAction:2);
		phaseA.poll;
		Out.ar(0, Pan2.ar(out * env, pan.linlin(0, 1, -1, 1)));
	};

	~oneShot = {
		arg buf=0
		,freq=220
		,volume=1
		,gate=1
		,f0=63.8.midicps
		,pan=0.2;
		var out = PlayBuf.ar(1, buf, BufRateScale.kr(buf) * freq / f0, doneAction: Done.freeSelf);
		var env = EnvGate(volume, gate, 0.1);
		Out.ar(0, Pan2.ar(out * env, pan.linlin(0, 1, -1, 1)));
	};

	~bambooBuf = Buffer.read(s, "BambooFlute.wav".resolveRelative);
	~ocarinaBuf = Buffer.read(s, "Ocarina.wav".resolveRelative);
	~beeBuf = Buffer.read(s, "BeeWithAttack.wav".resolveRelative);
	~highPluckBuf = Buffer.read(s, "HighPluck.wav".resolveRelative);
	~woodTapBuf = Buffer.read(s, "WoodTap.wav".resolveRelative);
	~whaleBuf = Buffer.read(s, "Whale.wav".resolveRelative);
	s.sync;
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\bamboo, {
			arg freq, volume=1, gate=1, pan=0.5;
			~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5) * 0.3,
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~bambooBuf,
				f0:198,
				loopStartTime:0.6,
				loopEndTime:3.6, // between 0 (min) and 1 (max)
				fadeTime:0.5,
			)
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\ocarina, {
			arg freq, volume=1, gate=1, pan=0.5;
			~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~ocarinaBuf,
				f0:51.8.midicps,
				loopStartTime:1,
				loopEndTime:19, // between 0 (min) and 1 (max)
				fadeTime:1.0,
			)
		});
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\bee, {
			arg freq, volume=1, gate=1, pan=0.5;
			~loopSound.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~beeBuf,
				f0:277,
				loopStartTime:1,
				loopEndTime:3, // between 0 (min) and 1 (max)
				fadeTime:0.3,
			)
		}).add;
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\highPluck, {
			arg freq, volume=1, gate=1, pan=0.5;
			~oneShot.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~highPluckBuf,
				f0:1595,
			)
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\woodTap, {
			arg freq, volume=1, gate=1, pan=0.5;
			~oneShot.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5) * 0.5,
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~woodTapBuf,
				f0:1601,
			)
		})
	);
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\whale, {
			arg freq, volume=1, gate=1, pan=0.5;
			~oneShot.value(
				freq: Lag.kr(freq, 0.5),
				volume: Lag.kr(volume, 0.5),
				gate: gate,
				pan: Lag.kr(pan, 1),
				buf:~whaleBuf,
				f0:316,
			)
		})
	);
	s.sync;
	// x = Synth(\bamboo, [\freq, 255, \pan, 0.8]);
}.fork;
)

// x.set(\freq, 2000)
// x.set(\gate, 0)