// Step 1: Go to Language>Quarks and install ScampUtils package
// Step 2: click anywhere in the text below and press command-enter to run
// Step 3: Go back to python and run the corresponding scamp code

(
s.waitForBoot({
	~gravBuf = Buffer.read(s, "TemplateWithData2.wav".resolveRelative);

	s.sync;

	ScampUtils.instrumentFromSynthDef(
		SynthDef(\gravPlayer, { |out=0, freq=(60.midicps), volume=1.0, gate=1, cutOff=1, templateMix=0.5, pan=0|
			var templateAndData = PlayBuf.ar(2, ~gravBuf, rate: freq/60.midicps, doneAction: 2);
			var mix = SelectX.ar(templateMix, templateAndData);
			Out.ar(0, Pan2.ar(mix * volume, pan) * EnvGate(gate:gate + (1 - cutOff.round), fadeTime:0.05));
		})
	);
});
)

// DEBUG: press command-enter on the line below and make sure that the port number matches the port number being used in the SCAMP osc part.
NetAddr.langPort