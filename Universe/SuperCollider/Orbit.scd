MarcUtilities.setOutputLimiter
MarcUtilities.doSpeakerTest(outputLevel:0.05)


~sources.freeAll;




(
// GLOBAL VARS
~reverbFFTsize = 4096;
~reverbIR = "IRs/ConcertHall.wav";
s.options.memSize = 2.pow(15);


~setUpGroups = {
	~sources = Group.new;
	~reverb = Group.after(~sources);
	~reverbBus = Bus.audio(s, 2);
};


~setUpSynthDefs = {
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
			var signalIn = In.ar(~reverbBus);
			Out.ar(out, PartConv.ar(signalIn, ~reverbFFTsize, ~irspectrums, 0.05));
		}).play(target:~reverb);
	}.fork;

	ScampUtils.instrumentFromSynthDef(
		SynthDef("organDonor",{
			arg out = 0, pan = 0.0, freq = 400, volume = 0.1, gate = 1, att = 0.01, dec = 0.5, sus = 1, rel = 0.5, lforate = 10, lfowidth = 0.01, cutoff = 2.75, rq = 0.5, distance=0.5;

			var vibrato, pulse, filter, env, panned;
			freq = Lag.kr(freq, 0.01);
			pan = Lag.kr((pan - 0.5) * 2, 0.01);
			volume = Lag.kr(volume / 2, 0.01);
			vibrato = SinOsc.ar(lforate, Rand(0, 2.0));
			// up octave, detune by 4 cents
			// 11.96.midiratio = 1.9953843530485
			// up octave and a half, detune up by 10 cents
			// 19.10.midiratio = 3.0139733629359

			freq = freq * [1, 1.9953843530485, 3.0139733629359];
			freq = freq * (1.0 + (lfowidth * vibrato));
			pulse = VarSaw.ar(
				freq: freq,
				iphase: Rand(0.0, 1.0) ! 3,
				width: Rand(0.3, 0.5) ! 3,
				mul: [1.0,0.7,0.3]);
			pulse = Mix(pulse);
			filter = RLPF.ar(pulse, (freq[0] * cutoff).min(5000), rq);
			env = EnvGen.ar(
				envelope: Env.adsr(att, dec, sus, rel, volume),
				gate: gate,
				doneAction: 2);

			panned = Pan2.ar(filter * env, pan);
			~distance.value(panned, distance, 0, ~reverbBus);
		}), target:~sources
	);
};


s.reboot;
s.waitForBoot({
	{
		MarcUtilities.setOutputLimiter;
		"Setting up groups...".post;
		~setUpGroups.value;	s.sync;
		"done.".postln;
		"Setting up SynthDefs...".post;
		~setUpSynthDefs.value; s.sync;
		"done.".postln;
	}.fork;
});
)
