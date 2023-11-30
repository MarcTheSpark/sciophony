

BambooFlute.wav

(
~loopSound = {
	arg buf=0
	,freq=220
	,sampleStart=0
	,loopStart=60000
	,loopLen=0.8 // between 0 (min) and 1 (max)
	,fadeTime=0.3
	,gate=1
	,attack=0.01
	,sustain=1
	,release=0.2
	,f0=220;

	var rate = freq / f0;
	var sr = rate*BufSampleRate.kr(buf);
	var fadeFrames = fadeTime*sr / rate;
	var loopEnd = loopLen*(BufFrames.kr(buf) - loopStart) + loopStart;
	var loopFrames = loopEnd - loopStart + 1;
	var loopTime = (loopFrames - fadeFrames)/sr;
	var startUpTime = (loopStart - sampleStart)/sr;

	var trigLoop = TDuty.ar(Dseq([startUpTime + loopTime, Dseq([loopTime], inf)]), gapFirst:1);

	var phaseA = Phasor.ar(trigLoop, rate, sampleStart, inf, loopStart);
	var phaseB = Phasor.ar(trigLoop, rate, loopEnd - fadeFrames, inf, loopEnd - fadeFrames);

	var srcA = BufRd.ar(buf.numChannels, buf, phaseA);
	var srcB = BufRd.ar(buf.numChannels, buf, phaseB);

	var startLoop = SetResetFF.ar(trigLoop);
	var loopPan = Phasor.ar(trigLoop, 2/fadeFrames * rate, -1, inf, -1).clip(-1,1);

	var out = Select.ar(startLoop, [srcA, LinXFade2.ar(srcB, srcA, pan:loopPan)]);
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, doneAction:2);

	Out.ar(0, Splay.ar(out) * env);
}
)

b = Buffer.read(s, "Bee.wav".resolveRelative);

SynthDef(\bamboo, {arg freq; ~loopSound.value(freq:freq, buf:b)}).add;

x = Synth(\bamboo, [\freq, 500]);
x.set(\gate, 0)

(
SynthDef(\simpler, {
	arg buf=0
	,freq=220
	,sampleStart=0
	,loopStart=60000
	,loopLen=0.8 // between 0 (min) and 1 (max)
	,fadeTime=0.3
	,gate=1
	,attack=0.01
	,sustain=1
	,release=0.2
	,f0=220;

	var rate = freq / f0;
	var sr = rate*BufSampleRate.kr(buf);
	var fadeFrames = fadeTime*sr / rate;
	var loopEnd = loopLen*(BufFrames.kr(buf) - loopStart) + loopStart;
	var loopFrames = loopEnd - loopStart + 1;
	var loopTime = (loopFrames - fadeFrames)/sr;
	var startUpTime = (loopStart - sampleStart)/sr;

	var trigLoop = TDuty.ar(Dseq([startUpTime + loopTime, Dseq([loopTime], inf)]), gapFirst:1);

	var phaseA = Phasor.ar(trigLoop, rate, sampleStart, inf, loopStart);
	var phaseB = Phasor.ar(trigLoop, rate, loopEnd - fadeFrames, inf, loopEnd - fadeFrames);

	var srcA = BufRd.ar(buf.numChannels, buf, phaseA);
	var srcB = BufRd.ar(buf.numChannels, buf, phaseB);

	var startLoop = SetResetFF.ar(trigLoop);
	var loopPan = Phasor.ar(trigLoop, 2/fadeFrames * rate, -1, inf, -1).clip(-1,1);

	var out = Select.ar(startLoop, [srcA, LinXFade2.ar(srcB, srcA, pan:loopPan)]);
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, doneAction:2);

	Out.ar(0, Splay.ar(out) * env);
}).add;


// Samples to load
b = Buffer.read(s, "BambooFlute.wav".resolveRelative);
// b = Buffer.read(s, "TrumpetBb4.wav".resolveRelative);


)

{
x = Synth(\bamboo, [\buf, b, \freq, 500]);
0.05.yield;
x.set(\gate, 0);
}.fork


(
SynthDef(\bamboo, {
	arg buf=0
	,freq=220
	,startTime=0
	,loopStartTime=0.8
	,loopEndTime=3.5 // between 0 (min) and 1 (max)
	,fadeTime=0.01
	,gate=1
	,attack=0.01
	,sustain=1
	,release=0.2
	,f0=220;

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
	var env = EnvGen.ar(Env.asr(attack, sustain, release, 1), gate, doneAction:2);

	Out.ar(0, Splay.ar(out) * env);
}).add;
)
