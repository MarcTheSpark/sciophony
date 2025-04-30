~initPositionStreams.value(rate:0.5);
~visualizeAll.value;
~sonifications.freeAll;

~changeStreamRates.value(1)

~startHarp.(~positionStreams[0], ~heightMaps[0], panRange:[-1, 1], ampRange:[0.01, 0.5], trigRateRange:[8, 28]);
~startHarp.(~positionStreams[1], ~heightMaps[0], scaleRootFreq: 125, panRange:[1, 1], ampRange:[0.01, 0.5], trigRateRange:[8, 28]);

~startGranulator.(~positionStreams[0], ~sourceMaps[0]);

~heightMaps[0].displayGUI;

~startSines.(~positionStreams[1]);


// ------------------------------------------------------- SETUP CODE (Run Once) ---------------------------------------------------------

(

~heightMaps = [
	HeightMap(200, 200, [
		[0.5, 0.8, 7, 3],
		[0.25, 0.3, 5, 5],
		[0.75, 0.3, 5, 5]
	]);
];

s.waitForBoot({
	~sourceMaps = [
		// MAP 1
		[
			Dictionary[
				\location -> [0.5, 0.9],
				\buf -> Buffer.read(s, "xylophoneOneNote.wav".resolveRelative),
				\sourceRange -> [0.2, 0.8]
			],
			Dictionary[
				\location -> [0.5, 0.1],
				\buf -> Buffer.read(s, "waterpipe.wav".resolveRelative),
				\sourceRange -> [0, 1]
			]
		],
	];
});

~initPositionStreams = {
	|rate=1|
	~positionStreams = [
		PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_left/datos_16.txt".resolveRelative, dt: 0.002),
	];
	~positionStreams.do({ |ps|
		ps.start(rate);
	});
	~sonifications = Group.new;


	//~heightMaps[0].displayGUI;
};

~changeStreamRates = { |rate|
	~positionStreams.do({ |ps|
		ps.changeRate(rate);
	});
};


thisThread.randSeed = 5;
~streamColors = Array.fill(50, {Color.rand});
~visualizeAll = {
	var canvas=nil;
	~positionStreams.do({ |ps, i|
		canvas = ps.visualize(canvas, showAccel:false, showVelocity:false, dotColor:~streamColors[i % ~streamColors.size]);
	});
};


~harpDefCount = 0;
~startHarp = {
	|positionStream, heightMap, scale=(Scale.minorPentatonic), scaleRootFreq=110,
	numStrings=25, pan="X", trigRateRange=#[12, 50], ampRange=#[0.2, 1.0], panRange=#[-1, 1]|

	var heightMapRange = heightMap.range;

	~harpDefCount = ~harpDefCount + 1;

	SynthDef((\harppluck ++ ~harpDefCount).asSymbol, {
		var position = positionStream.pos;
		var speed = positionStream.speed(0.05);
		var height = heightMap.interp(position[0], position[1]);
		var rate = 12;
		var mainTrig = Impulse.kr(speed.linexp(0, 2, trigRateRange[0], trigRateRange[1]));
		var trigIndex = height.linlin(heightMapRange[0], heightMapRange[1], 0, numStrings).round;
		var amp = speed.linlin(0, 2, ampRange[0], ampRange[1]) * 0.1;

		var plucks = Array.fill(numStrings, { |i|
			var freq = scale.degreeToFreq(i, scaleRootFreq , 0);
			var env = Env.new([0,1, 1, 0],[0.001,0.006, 0.0005],[5,-5, -8]);
			var inp = amp * LFClipNoise.ar(2000) * EnvGen.ar(env, mainTrig * BinaryOpUGen('==', trigIndex, i));
			// the LFNoise here creates a fun detuning effect. Try increasing it.
			var plucker = DWGPluckedStiff.ar(freq * LFNoise2.kr(0.1).linexp(-1, 1, 0.99, 1.01), amp, c1:4, c3:20, inp:inp, release:1, fB:80);
			Pan2.ar(
				plucker,
				position[0].linlin(0, 1, panRange[0], panRange[1])
			);
		});
		Out.ar(0, Mix.ar(plucks));
	}).play(target: ~sonifications);
};


~granulatorDefCount = 0;
~startGranulator = {
	|positionStream, sourceMap, trigRateRange=#[30, 80], ampRange=#[0.2, 1.0], durRange=#[0.05, 0.05], panRange=#[-1, 1]|
	~granulatorDefCount = ~granulatorDefCount + 1;

	SynthDef((\positionGranulator ++ ~granulatorDefCount).asSymbol, {
		var pos = positionStream.pos(0.1);
		var speed = positionStream.speed(0.1);

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
		var mainTrig = Impulse.kr(speed.linlin(0, 2, trigRateRange[0], trigRateRange[1]));

		// Create grains for each buffer, modulating their amplitudes based on distance
		var grains = Mix(sourceMap.collect { |src, i|
			GrainBuf.ar(
				2,
				mainTrig,
				speed.linexp(0, 2, durRange[0], durRange[1]),
				src[\buf].bufnum,
				pos[0].linexp(0, 1, 1.1, 1.6),
				WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]),
				2,
				pos[0].linlin(0, 1, panRange[0], panRange[1])
			) * volumes[i] * speed.linlin(0, 2, ampRange[0], ampRange[1]);
		});

		// Output the mixed grains, scaled by amp
		Out.ar(0, grains);
	}).play(target:~sonifications);
};

~startSines = {
	|positionStream, freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linlin(0, 2, 0, 0.3)"|
	SynthDef(\sines0, {
		var paramIntepreter = positionStream.getParamInterpreter;
		freq = paramIntepreter.(freq);
		vol = paramIntepreter.(vol);
		freq.poll;
		vol.poll;
		Out.ar(0, SinOsc.ar(freq, mul:vol));
	}).play(target:~sonifications);
};
)
