// Step 1: Go to Language>Quarks and install ScampUtils package
// Step 2: click anywhere in the text below and press command-enter to run
// Step 3: Go back to python and run the corresponding scamp code

(
s.waitForBoot({
	// Load all the recordings into ~recordings, interleaved as template, data, template data, etc.
	var recordingsFolder, recordingsDict, recordingNames;
	recordingsDict = Dictionary.new;
	recordingsFolder = PathName.new("Recordings".resolveRelative);
	recordingsFolder.files.do({ |file|
		if(file.extension == "wav", {
			var fileName = file.fileNameWithoutExtension;
			var fileNameComponents = fileName.split($-);
			if(fileName.contains("template"), {
				var recordingName = fileNameComponents[0].asSymbol;
				if(recordingsDict.includesKey(recordingName).not, {
					recordingsDict[recordingName] = Dictionary.new;
				});
				recordingsDict[recordingName]["template"] = Buffer.read(s, file.fullPath);
			}, {
				var recordingName = fileNameComponents[1].asSymbol;
				if(recordingsDict.includesKey(recordingName).not, {
					recordingsDict[recordingName] = Dictionary.new;
				});
				recordingsDict[recordingName]["data"] = Buffer.read(s, file.fullPath);
			});
		});
	});
	recordingNames = recordingsDict.keys.asList.sort;
	~recordings = Array.fill(recordingNames.size * 2, { |i|
		i.even.if({
			recordingsDict[recordingNames[i / 2]]["template"]
		}, {
			recordingsDict[recordingNames[(i / 2).asInteger]]["data"]
		});
	});

	// wait for the recordings to be loaded
	s.sync;

	// SynthDef with backupDur (how far before the pop to start), decayTime (how quickly to decay after the pop), and which (which recording 0-10) parameters
	ScampUtils.instrumentFromSynthDef(
		SynthDef(\gravPlayer, { |out=0, freq=261.6255653006, volume=1.0, gate=1, backupDur=1, pan=0, templateMix=0.1, attackTime=0.01, decayTime=1, which=8|
			var rate = freq/60.midicps;
			var templateBuf = Select.kr(2 * which, ~recordings);
			var dataBuf = Select.kr((2 * which) + 1, ~recordings);
			var startPos = BufFrames.ir(templateBuf) - (2 * BufSampleRate.ir(templateBuf)) - (rate * backupDur * BufSampleRate.ir(templateBuf));
			var bufTrig = startPos + (Sweep.ar * BufSampleRate.ir(templateBuf) * rate);
			var templatePlayer = PlayBuf.ar(1, templateBuf, rate: BufRateScale.ir(templateBuf) * rate * (bufTrig > 0), startPos: startPos);
			var dataPlayer = PlayBuf.ar(1, dataBuf, rate: BufRateScale.ir(dataBuf) * rate * (bufTrig > 0), startPos: startPos);
			var sig = SelectX.ar(templateMix, [templatePlayer, dataPlayer]);
			sig = Pan2.ar(sig * volume, pan);
			sig = sig * EnvGen.ar(Env.adsr(attackTime:attackTime, decayTime:decayTime), gate:gate, doneAction:2);
			Out.ar(out, sig);
		})
	);
});
)

// DEBUG: press command-enter on the line below and make sure that the port number matches the port number being used in the SCAMP osc part.
NetAddr.langPort