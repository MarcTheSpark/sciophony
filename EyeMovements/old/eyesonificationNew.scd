(
w = Window.new("The Four Noble Truths");

Button(w, Rect(20, 20, 340, 30))
        .states_([
            ["Launch", Color.white, Color.black],
        ])
        .action_({ arg butt;
            ~streamManager.runSonification(30.rand, ~whistle.value(rq:"~x.linexp(0, 1, 0.001, 0.5)"))
        });
Button(w, Rect(20, 100, 340, 30))
        .states_([
            ["Stop", Color.white, Color.black],
        ])
        .action_({ arg butt;
            ~streamManager.killSonifications;
        });
w.front;
)

(
{
	~streamManager.rate = 0.5;
	5.do { |i|
		i.postln;
		~streamManager.runSonification(i, ~whistle.value(rq:"Lag.kr(~s).linexp(0, 4, 0.001, 2)"));
		(1 + 3.rand).yield;
	};
	10.yield;
	5.reverseDo({ |i|
		~streamManager.killSonifications([i]);
		(1 + 3.rand).yield;
	})

}.fork
)

(
{
	var killSon;
	~streamManager.rate = 0.1;
	killSon = ~streamManager.runSonification(5, ~harpStrum.value(pitchHeight:"~heightMaps[0].interp(~x, ~y)"));
	10.yield;
	killSon.value;
}.fork
)

~streamManager.start

(
r = {
	var thisRoutine = thisThread;
	~streamManager.rate = 0.5;
	8.do { |i|
		i.postln;
		thisFunction.postln;
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
	10.yield;
	8.reverseDo({ |i|
		~streamManager.killSonifications([i]);
		(0.5 + 2.rand).yield;
	});
}.fork
)



~streamManager.killSonifications([16])

(
c = ~streamManager.runSonification(16, ~whistle.value(
	freq:"~x.linexp(0, 2, 3000, 9000)",
	rq:"~x.linexp(0, 1, 0.001, 0.5)"
))
)
c.value
d = ~streamManager.runSonification(16, ~harpStrum.value(amp:"~s.linexp(0, 2, 0.01, 0.02)"));
d.value

~streamManager.synthsOnStreams[15][0].set(\gate, 0)

(

var streamfiles = Array.fill(30, { |i| ("Marc_eyes/eyes_track_samples/tracks_3840/portrait_191/191_left/datos_" ++ (i + 1).asString ++ ".txt").resolveRelative});

s.waitForBoot({
	"Loading Eye Sonification Setup...".postln;
	~streamManager = PositionStreamGroup.new(streamfiles, canvas:PositionStream.makeVisualizationCanvas, sendOsc:true, streamsRect: Rect.newSides(0, 0, 2160, 3840));
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

	~sounds = Dictionary[
		\xylophone -> Buffer.read(s, "sounds/xylophoneOneNote.wav".resolveRelative),
		\waterpipe -> Buffer.read(s, "sounds/waterpipe.wav".resolveRelative),
		\puff -> Buffer.read(s, "sounds/puff.wav".resolveRelative),
		\bat -> Buffer.read(s, "sounds/bat1.wav".resolveRelative),
		\clicks -> Buffer.readChannel(s, "sounds/clicks.wav".resolveRelative, channels:[0]),
		\whispers -> Buffer.readChannel(s, "sounds/whispers.wav".resolveRelative, channels:[0]),
	];

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


	~harpStrum = {
		|scale=(Scale.minorPentatonic), scaleRootFreq=110, numStrings=25, pitchHeight="~y", trigRate="~s.linlin(0, 2, 6, 28)", amp="~s.linexp(0, 2, 0.02, 0.2)", pan="~x"|

		{ |positionStream| { |gate=1|
			var paramInterpreter = positionStream.getParamInterpreter;
			var pitchHeightInterpreted = paramInterpreter.(pitchHeight);
			var trigRateInterpreted = paramInterpreter.(trigRate);
			var ampInterpreted = paramInterpreter.(amp);
			var panInterpreted = paramInterpreter.(pan);
			var mainTrig = Impulse.kr(trigRateInterpreted);
			var trigIndex = pitchHeightInterpreted.linlin(0, 1, 0, numStrings).floor;

			var plucks = Array.fill(numStrings, { |i|
				var freq = scale.degreeToFreq(i, scaleRootFreq , 0);
				var env = Env.new([0,1, 1, 0],[0.001,0.006, 0.0005],[5,-5, -8]);
				var inp = ampInterpreted * LFClipNoise.ar(2000) * EnvGen.ar(env, mainTrig * BinaryOpUGen('==', trigIndex, i));
				// the LFNoise here creates a fun detuning effect. Try increasing it.
				var plucker = DWGPluckedStiff.ar(freq * LFNoise2.kr(0.1).linexp(-1, 1, 0.99, 1.01), ampInterpreted, c1:4, c3:20, inp:inp, release:1, fB:80);
				Pan2.ar(
					plucker,
					panInterpreted
				);
			});
			Out.ar(0, Mix.ar(plucks) * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};


	~mapGranulator = {
		|sourceMap, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)"|

		{ |positionStream| { |gate=1|
			var paramInterpreter = positionStream.getParamInterpreter;
			var pos = paramInterpreter.("[~x, ~y]");
			var trigRateInterpreted = paramInterpreter.(trigRate);
			var ampInterpreted = paramInterpreter.(amp);
			var durInterpreted = paramInterpreter.(dur);
			var panInterpreted = paramInterpreter.(pan);

			// Calculate distances to each source location
			var distances = sourceMap.collect { |src|
				var locX = src[\location][0];
				var locY = src[\location][1];
				hypot(pos[0] - locX, pos[1] - locY); // Euclidean distance
			};

			// Invert distances to create probabilities (closer distance -> higher probability)
			var invDistances = distances.collect { |dist| 1 / (dist + 0.001) }; // Small offset to avoid division by zero

			// Normalize the inverted distances to sum to 1
			var total = invDistances.sum;
			var volumes = (invDistances / total).pow(1.5) * 2;

			// Main trigger
			var mainTrig = Impulse.kr(trigRateInterpreted);

			// Create grains for each buffer, modulating their amplitudes based on distance
			var grains = Mix(sourceMap.collect { |src, i|
				GrainBuf.ar(
					2,
					mainTrig,
					durInterpreted,
					src[\buf].bufnum,
					pos[0].linexp(0, 1, 1.1, 1.6),
					WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]),
					2,
					panInterpreted
				) * volumes[i] * ampInterpreted;
			});

			// Output the mixed grains, scaled by amp
			Out.ar(0, grains * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};

	~simpleSines = {
		|freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)"|
		{ |positionStream| { |gate=1|
			var paramInterpreter = positionStream.getParamInterpreter;

			freq = paramInterpreter.(freq);
			vol = paramInterpreter.(vol);
			pan = paramInterpreter.(pan);
			Out.ar(0, Pan2.ar(SinOsc.ar(freq, mul:vol), pan) * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};

	~whistle = {
		|freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)", rq="0.005"|
		{ |positionStream| { |gate=1|
			var whistle;
			var paramInterpreter = positionStream.getParamInterpreter;
			freq = paramInterpreter.(freq);
			vol = paramInterpreter.(vol);
			pan = paramInterpreter.(pan);
			rq = paramInterpreter.(rq);
			whistle = BPF.ar(PinkNoise.ar, freq, rq, mul:vol/rq);
			Out.ar(0, Pan2.ar(whistle, pan) * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};


	~saccadeTrigger = {
		|soundBuf, rate="~s.linexp(0, 4, 0.5, 1.5)", amp="~s.linexp(0, 4, 0.2, 0.5)", pan="~x.linlin(0, 1, -1, 1)", startTime=0|
		{ |positionStream| { |gate=1|
			var paramInterpreter = positionStream.getParamInterpreter;
			rate = paramInterpreter.(rate);
			amp = paramInterpreter.(amp);
			pan = paramInterpreter.(pan);
			Out.ar(0, Pan2.ar(
				PlayBuf.ar(soundBuf.numChannels, soundBuf, rate:rate, trigger: positionStream.detectSaccades, startPos: startTime * SampleRate.ir) * amp * EnvGate(gate:gate, fadeTime:0.15),
				pan
			));
		} };
	};


	~simpleGranulator = {
		|soundBuf, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.5, 0.5)"|

		{ |positionStream| { |gate=1|
			var grains;
			var paramInterpreter = positionStream.getParamInterpreter;
			trigRate = paramInterpreter.(trigRate);
			amp = paramInterpreter.(amp);
			dur = paramInterpreter.(dur);
			pan = paramInterpreter.(pan);
			playRate = paramInterpreter.(playRate);
			playPos = paramInterpreter.(playPos);

			// Create grains for each buffer, modulating their amplitudes based on distance
			grains = GrainBuf.ar(
				2,
				Impulse.kr(trigRate),
				dur,
				soundBuf,
				playRate,
				playPos,
				2,
				pan
			);

			// Output the mixed grains, scaled by amp
			Out.ar(0, grains * amp * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};

	~velTrigger = {
		|soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="800"|
		{ |positionStream| { |gate=1|
			var player, env;
			var trig = (positionStream.speed.lag(0.2) > speedThresh);
			var paramInterpreter = positionStream.getParamInterpreter;
			envelope = paramInterpreter.(envelope);
			amp = paramInterpreter.(amp);
			pan = paramInterpreter.(pan);
			playRate = paramInterpreter.(playRate);
			playPos = paramInterpreter.(playPos);
			bpfFreq = paramInterpreter.(bpfFreq);
			player = PlayBuf.ar(1, soundBuf, trigger: trig, startPos: WhiteNoise.kr(0.4, 0.5) * BufFrames.ir(soundBuf));
			env = EnvGen.kr(envelope, trig, amp);
			Out.ar(0, Pan2.ar(BPF.ar(player * env, bpfFreq), pan) * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};

	~velTriggerRingMod = {
		|soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="~y.linexp(0, 1, 3000, 400)", ringFreq="~y.linexp(0, 1, 3000, 400)"|
		{ |positionStream| { |gate=1|
			var player, env;
			var trig = (positionStream.speed.lag(0.2) > speedThresh);
			var paramInterpreter = positionStream.getParamInterpreter;
			envelope = paramInterpreter.(envelope);
			amp = paramInterpreter.(amp);
			pan = paramInterpreter.(pan);
			playRate = paramInterpreter.(playRate);
			playPos = paramInterpreter.(playPos);
			bpfFreq = paramInterpreter.(bpfFreq);
			ringFreq = paramInterpreter.(ringFreq);
			player = PlayBuf.ar(1, soundBuf, trigger: trig, startPos: WhiteNoise.kr(0.4, 0.5) * BufFrames.ir(soundBuf));
			env = EnvGen.kr(envelope, trig, amp);
			Out.ar(0, Pan2.ar(BPF.ar(player * env, bpfFreq) * SinOsc.ar(bpfFreq), pan) * EnvGate(gate:gate, fadeTime:0.15));
		} };
	};


	Document.globalKeyDownAction = {
		arg document, char, modifiers, unicode, keycode;

		if (modifiers.isCtrl && keycode == 44) { // ctrl+,
			~streamManager.killSonifications(hard:true);
		}
	};

	s.sync;
	MarcUtilities.setOutputLimiter(0.7, 0.7);
	"Done!".postln;

});

)
