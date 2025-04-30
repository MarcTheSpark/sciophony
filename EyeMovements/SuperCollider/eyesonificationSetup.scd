/**
Defines the ~doSetup function, which creates:
  - ~streamManager, a PositionStreamGroup for all of the eye trackers
  - ~heightMaps, a list of HeightMap objects
  - ~sounds (auto-populated dictionary of name -> buffer from the sounds directory),
  - ~rescanSounds (function that re-populates ~sounds)
  - ~sourceMaps (a list of lists (each a source map) of dictionaries (each a source)) used by ~mapGranulator
Also sets up a global reverb and limiter
**/

~doSetup = { |canvas=true, onSetup=nil|

	var streamfiles = Array.fill(30, { |i| ("eye_tracking_data/tracks_3840/portrait_191/191_left/datos_" ++ (i + 1).asString ++ ".txt").resolveRelative});

	s.waitForBoot({
		"Loading Eye Sonification Setup...".postln;
		~sources = Group.new;
		~effects = Group.after(~sources);
		~mixBus = Bus.new;
		~streamManager = PositionStreamGroup.new(streamfiles, playbackGroup:~sources, canvas:canvas.if{PositionStream.makeVisualizationCanvas}{nil}, sendOsc:true, streamsRect: Rect.newSides(0, 0, 2160, 3840));
		s.sync;
		~streamManager.start;
		~streamManager.showActiveStreams();

		~heightMaps = [
			HeightMap(200, 200, [
				[0.5, 0.8, 7, 3],
				[0.25, 0.3, 5, 5],
				[0.75, 0.3, 5, 5]
			]);
		];


		// Function to load all WAV files from a directory
		~rescanSounds = {
			var path = "sounds/".resolveRelative;
			var files, soundFiles;

			~sounds = Dictionary.new;
			// Get all files in the directory
			files = PathName(path).files;

			// Filter to only include .wav files (case insensitive)
			soundFiles = files.select({ |file|
				var extension = file.extension.toLower;
				extension == "wav";
			});

			// Create dictionary entries for each sound file
			soundFiles.do({ |file|
				var key = file.fileNameWithoutExtension.asSymbol;
				var buffer;

				// Check if the file has multiple channels, and handle appropriately
				buffer = Buffer.read(s, file.fullPath);

				// Add to dictionary with the filename (without extension) as the key
				~sounds.put(key, buffer);

				// Optional: Print confirmation of loaded sounds
				("Loaded sound: " ++ key).postln;
			});

			// Return the number of sounds loaded
			"Loaded % sound files.".format(soundFiles.size).postln;
			soundFiles.size;
		};
		~rescanSounds.value;

        ~sourceMaps = [
            // MAP 1
            [
                Dictionary[
                    \location -> [0.5, 0.9],
                    \buf -> ~sounds[\xylophone],
                    \sourceRange -> [0.2, 0.8]
                ],
                Dictionary[
                    \location -> [0.5, 0.1],
                    \buf -> ~sounds[\waterpipe],
                    \sourceRange -> [0, 1]
                ]
            ],
        ];

        this.executeFile("sonificationFunctions.scd".resolveRelative);

		Document.globalKeyDownAction = {
			arg document, char, modifiers, unicode, keycode;

			if (modifiers.isCtrl && keycode == 44) { // ctrl+,
				~streamManager.killSonifications(hard:true);
			}
		};


		~reverbFFTsize = 4096;
		~reverbIR = "sounds/ConcertHallIR.wav";
		s.options.memSize = 2.pow(15);
		~outBus = 0;


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
				var signalIn = In.ar(~mixBus, 2);
				var reverbed = PartConv.ar(signalIn, ~reverbFFTsize, ~irspectrums, 0.05);
				Out.ar(~outBus,signalIn + reverbed);
			}).play(target:~effects);
		}.fork;

		s.sync;
		EyeUtilities.setOutputLimiter(0.7, 0.7);
		"Done!".postln;
		onSetup.value;
	});

}