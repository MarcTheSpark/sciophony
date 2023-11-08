// Step 1: Go to Language>Quarks and install ScampUtils package
// Step 2: click anywhere in the text below and press command-enter to run
// Step 3: Go back to python and run the corresponding scamp code

(
s.waitForBoot({
	~templateBuf = Buffer.read(s, "Recordings/GW170817-template.wav".resolveRelative);
	~dataBuf = Buffer.read(s, "Recordings/H1-GW170817-data.wav".resolveRelative);

	s.sync;

	ScampUtils.instrumentFromSynthDef(
		SynthDef(\gravPlayer, { |out=0, freq=261.6255653006, volume=1.0, gate=1, backupDur=1, pan=0, templateMix=0.1, decayTime=1|
			var rate = freq/60.midicps;
			var startPos = BufFrames.ir(~templateBuf) - (2 * BufSampleRate.ir(~templateBuf)) - (rate * backupDur * BufSampleRate.ir(~templateBuf));
			var bufTrig = startPos + (Sweep.ar * BufSampleRate.ir(~templateBuf) * rate);
			var templatePlayer = PlayBuf.ar(1, ~templateBuf, rate: BufRateScale.ir(~templateBuf) * rate * (bufTrig > 0), startPos: startPos);
			var dataPlayer = PlayBuf.ar(1, ~dataBuf, rate: BufRateScale.ir(~dataBuf) * rate * (bufTrig > 0), startPos: startPos);
			var sig = SelectX.ar(templateMix, [templatePlayer, dataPlayer]);
			sig = Pan2.ar(sig * volume, pan);
			sig = sig * EnvGen.ar(Env.adsr(decayTime:decayTime), gate:gate, doneAction:2);
			Out.ar(out, sig);
		})
	);
});
)

// DEBUG: press command-enter on the line below and make sure that the port number matches the port number being used in the SCAMP osc part.
NetAddr.langPort