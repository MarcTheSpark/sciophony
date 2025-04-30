// Useful one liners
~streamManager.rate = 0.5;  // change the rate of eye movement
~rescanSounds.value;  // rescan sounds
~streamManager.setDrawMethod(0); // change the draw method
~streamManager.killSonifications(hard:true);  // kill sonification without messing other stuff up(can also type ctrl-comma)


// MAIN ENTRY POINT, RUN THIS TO SET UP EVERYTHING
(
var showSCCanvas = false;

this.executeFile("eyesonificationSetup.scd".resolveRelative);
this.executeFile("eyesonificationGUI.scd".resolveRelative);
~doSetup.value(showSCCanvas, {
	~streamManager.rate = 0.5;

	~sonificationMethods = Dictionary[
		\whistles -> { |streamNums|
			streamNums.do { |streamNum|
				~streamManager.runSonification(streamNum, ~whistle.value(
					freq:"~x.linexp(0, 2, 3000, 9000)",
					rq:"~x.linexp(0, 1, 0.001, 0.5)"
				));
			}
		},
		\leaves -> { |streamNums|
			streamNums.do { |streamNum|
				~streamManager.runSonification(streamNum, ~velTriggerChoice.value(
					[~sounds[\leafHit1], ~sounds[\leafHit2], ~sounds[\leafHit3], ~sounds[\leafHit4]],
					rq: "50",
					bpfFreq: "~y.linexp(0, 1, 1000, 5000)",
					speedThresh: 1,
					amp:"~s.linexp(0, 2, 0.2, 0.8)",
				));
			}
		},
		\chatter-> { |streamNums|
			streamNums.do { |streamNum|
				/* Granulator Default Params
				|soundBuf, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.5, 0.5)", synchronous=true|
				*/
				~streamManager.runSonification(streamNum, ~simpleGranulator.value(
					~sounds[\talking],
					playRate: 1.0.rand.linexp(0, 1, 0.8, 1.2).asString,
					/*				dur: "1/~s.linlin(0, 2, 5, 30)",
					trigRate:"~s.linlin(0, 2, 5, 30)",*/
				));
			}
		},
		\grainBuild -> { |streamNums|
			{
				var thisRoutine = thisThread;
				streamNums.do { |i|
					~streamManager.runSonification(i, ~simpleGranulator.value(
						i.mod(3).switch (
							0, {~sounds[\whispers]},
							1, {~sounds[\clicks]},
							2, {~sounds[\waterpipe]},
						),
						playRate:"0.7 + ~heightMaps[0].interp(~x, ~y).linexp(0, 1, 0.1, 2.0)",
					), onCancel: { thisRoutine.stop; });
					(1 + 3.rand).yield;
				};
			}.fork
		}
	];


	~gui = ~setupGUI.value(
		sonificationNames: ~sonificationMethods.keys.asArray.sort,
		launchCallback: { |selectedStreams|
			~sonificationMethods[~gui.getSonificationMethod].value(selectedStreams);
			~gui.unselectAllStreams;
		},
		endCallback: { |selectedStreams|
			~streamManager.killSonifications(selectedStreams);
			~gui.unselectAllStreams;
		},
		endAllCallback: {
			~streamManager.killSonifications;
		}
	);

	// Setup number overlays so that we know how many synths are running on a given stream
	{
		loop {
			~gui.gridToggle.setNumberOverlays(~streamManager.synthsOnStreams.collect({|l| l.size}));
			0.1.yield;
		}
	}.fork;
});
)



// EXPERIMENTS, EXTRA NONSENSE
(
c = ~streamManager.runSonification(16, ~whistle.value(
	freq:"~x.linexp(0, 2, 3000, 9000)",
	rq:"~x.linexp(0, 1, 0.001, 0.5)"
))
)
c.value
