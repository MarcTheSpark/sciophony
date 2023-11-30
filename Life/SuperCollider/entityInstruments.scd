(
s.waitForBoot(
	{
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
			Out.ar(0,  Pan2.ar(out * env * volume, pan.linlin(0, 1, -1, 1)));
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
			Out.ar(0, Pan2.ar(out * env * volume, pan.linlin(0, 1, -1, 1)));
		};

		~bambooBuf = Buffer.read(s, "Audio/BambooFlute.wav".resolveRelative);
		~ocarinaBuf = Buffer.read(s, "Audio/Ocarina.wav".resolveRelative);
		~beeBuf = Buffer.read(s, "Audio/BeeWithAttack.wav".resolveRelative);
		~highPluckBuf = Buffer.read(s, "Audio/HighPluck.wav".resolveRelative);
		~woodTapBuf = Buffer.read(s, "Audio/WoodTap.wav".resolveRelative);
		~whaleBuf = Buffer.read(s, "Audio/Whale.wav".resolveRelative);
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
					loopStart:0.6,
					loopEnd:3.6, // between 0 (min) and 1 (max)
					fadeTime:0.5,
				)
			})
		);
		ScampUtils.instrumentFromSynthDef(
			SynthDef(\ocarina, {
				arg freq, volume=1, gate=1, pan=0.5;
				~loopSound.value(
					freq: Lag.kr(freq, 1.2),
					volume: Lag.kr(volume, 0.5),
					gate: gate,
					pan: Lag.kr(pan, 1),
					buf:~ocarinaBuf,
					f0:51.8.midicps,
					loopStart:1,
					loopEnd:19, // between 0 (min) and 1 (max)
					fadeTime:1.0,
				)
			});
		);
		ScampUtils.instrumentFromSynthDef(
			SynthDef(\bee, {
				arg freq, volume=1, gate=1, pan=0.5;
				~loopSound.value(
					freq: Lag.kr(freq, 0.5),
					volume: Lag.kr(volume, 0.5) * 2,
					gate: gate,
					pan: Lag.kr(pan, 1),
					buf:~beeBuf,
					f0:277,
					loopStart:1,
					loopEnd:3, // between 0 (min) and 1 (max)
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
					volume: Lag.kr(volume, 0.5) * 0.35,
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
		// s.sync;
		// x = Synth(\bamboo, [\freq, 440, \pan, 0.8]);
	}
);
)
