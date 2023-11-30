~bambooBuf = Buffer.read(s, "BambooFlute.wav".resolveRelative);

(
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

	var trigLoopA = TDuty.ar(Dseq([loopEnd - sampleStart + loopFrames - (2 * loopTime), Dseq([loopTime], inf)]), gapFirst:1);

	var phaseA = Phasor.ar(trigLoop, rate, sampleStart, inf, loopStart);
	var phaseB = Phasor.ar(trigLoop, rate, loopEnd - fadeFrames, inf, loopEnd - fadeFrames);

	var srcA = BufRd.ar(buf.numChannels, buf, phaseA);
	var srcB = BufRd.ar(buf.numChannels, buf, phaseB);

	var startLoop = SetResetFF.ar(trigLoop);
	var loopPan = Phasor.ar(trigLoop, 2/fadeFrames * rate, -1, inf, -1).clip(-1,1);

	// var out = Select.ar(startLoop, [srcA, LinXFade2.ar(srcB, srcA, pan:loopPan)]);
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, volume, doneAction:2);
	phaseA.poll;
	Out.ar(0, Pan2.ar(out * env, pan.linlin(0, 1, -1, 1)));

};
)






(
~resetFirstTimeDifferent = {
	arg firstResetDur, subsequentResetDur, rate=1;
	var initialImpulsePhase = 1 - (firstResetDur.mod(subsequentResetDur) / subsequentResetDur);
	(Sweep.ar(rate:rate) > firstResetDur) * Impulse.ar(rate/subsequentResetDur, phase:initialImpulsePhase);
};

~introLoopBufPhasor = {
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
	arg t, start=2, loopStart=7, loopEnd=12, fadeLength=2;
	var cycleStart = loopEnd - start - fadeLength;
	var loopLength = loopEnd - loopStart;
	var flatLength = loopLength - (2 * fadeLength);
	var cycleLength = 2 * (flatLength + fadeLength);
	var tCycle = (t - cycleStart).mod(cycleLength);
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

	var rate = MouseX.kr(0.2, 10, 1);//freq / f0;
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, volume, doneAction:2);
	var loopDur = loopEnd - loopStart;
	var phaseA = ~introLoopBufPhasor.value(buf, start, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * start).min(BufSampleRate.ir(buf) * loopEnd);
	var phaseB = ~introLoopBufPhasor.value(buf, loopStart + fadeTime - loopEnd, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * loopStart).min(BufSampleRate.ir(buf) * loopEnd);
	var whichPhase = ~fadeCycle.value(Sweep.ar(rate:rate), start, loopStart, loopEnd, fadeTime);
	var out = SelectX.ar(whichPhase, [BufRd.ar(1, buf, phaseA), BufRd.ar(1, buf, phaseB)]);
	Out.ar(0, out);
};
)

EnvGen
{~loopSound.value(~bambooBuf, [\loopStart, 2.5, \loopEnd, 3, \fadeTime, 0.1])}.play



(
~fadeCycle = {
	arg t, start=2, loopStart=7, loopEnd=12, fadeLength=2;
	var cycleStart = loopEnd - start - fadeLength;
	var loopLength = loopEnd - loopStart;
	var flatLength = loopLength - (2 * fadeLength);
	var cycleLength = 2 * (flatLength + fadeLength);
	var t = Sweep.ar;
	var tCycle = (t - cycleStart).mod(cycleLength);
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
)

Case
SynthDef(\fs, ~fadeCycle).play(args: []);

Array.fill(300, {|x| var t = x / 10; ~fadeCycle.value(2, 7, 12, 2, t)}).plot

(1 < 3 && 3 < 4)


~fadeCycle = {
	arg start, loopStart, loopEnd, fadeLength, t;
	var cycleStart = loopEnd - start - fadeLength;
	var loopLength = loopEnd - loopStart;
	var flatLength = loopLength - (2 * fadeLength);
	var cycleLength = 2 * (flatLength + fadeLength);
	var tCycle = (t - cycleStart).mod(cycleLength);

	case
    { t < cycleStart } { 0 }
    { tCycle < fadeLength } { tCycle / fadeLength }
	{ (fadeLength <= tCycle) && (tCycle < (fadeLength + flatLength))} { 1 }
	{ ((fadeLength + flatLength) <= tCycle) && (tCycle < ((2 * fadeLength) + flatLength))} { 1 - ((tCycle - fadeLength - flatLength) / fadeLength)}
    { true } { 0 }
};



~loopSound = {
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
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, volume, doneAction:2);
	var loopDur = loopEnd - loopStart;
	var phaseA = ~introLoopBufPhasor.value(buf, start, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * start).min(BufSampleRate.ir(buf) * loopEnd);
	var phaseB = ~introLoopBufPhasor.value(buf, loopStart + fadeTime - loopEnd, loopStart, loopEnd + loopDur - (2 * fadeTime), rate).max(BufSampleRate.ir(buf) * loopStart).min(BufSampleRate.ir(buf) * loopEnd);
	var phaseEnv = EnvGen.ar(Env(
		[0, 0, 1, 1, 0, 0, 1],
		[
			loopEnd - start - fadeTime,
			fadeTime,
			loopEnd - loopStart - (2 * fadeTime),
			fadeTime,
			loopEnd - loopStart - (2 * fadeTime)
		],
		releaseNode: 5,
		loopNode: 1,
	), timeScale: (1/rate));
	Out.ar(0, [BufRd.ar(1, buf, phaseA), phaseEnv]);
}