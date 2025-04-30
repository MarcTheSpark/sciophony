
~showStreams.value;
~hideStreams.value;



// ----------------------------------------------- Sonifications ---------------------------------------

~startHarp.(~positionStreams[0], scaleRootFreq: 110, pitchHeight:"~heightMaps[0].interp(~x, ~y)", pan:"~x.linlin(0, 1, -1, 1)", amp:"~s.linexp(0, 2, 0.02, 0.05)")
~startHarp.(~positionStreams[1], scaleRootFreq: (110 * 5 / 4), pitchHeight:"~heightMaps[0].interp(~x, z~y)", pan:"~x.linlin(0, 1, -1, 1)")

~startMapGranulator.(~positionStreams[0], ~sourceMaps[0], trigRate:"~x.linexp(0, 1, 5, 50)", amp:"~s.linexp(0, 2, 0.2, 3.0)");


~startSines.(~positionStreams[1]);
~startSines.(~positionStreams[1], freq:"~heightMaps[0].interp(~x, ~y).linexp(0, 1, 300, 1500)", vol:"0.1");


~positionStreams[0].visualize(showAccel:false, showVelocity:false, dotColor:~streamColors[0])
~startSaccadeTrigger.(~positionStreams[0], ~sounds[\waterpipe], amp:"0.01", rate:"(~x + ~y).linexp(0, 2, 0.5, 1.5)");

~startSimpleGranulator.(~positionStreams[0], ~sounds[\puff], amp:"~s.linexp(0, 2, 0.01, 0.2)");
~startSimpleGranulator.(~positionStreams[0], ~sounds[\waterpipe], amp:"~s.linexp(0, 2, 0.2, 0.01)", playRate:"~s.linexp(0, 2, 0.9, 1.0)");


~visualizeStreams.value([6]);
~startVelTrigger.(~positionStreams[6], ~sounds[\whispers], speedThresh:2, envelope:"Env.perc(0.1, 1.4)", amp:"~s.linexp(0, 2, 0.02, 0.3)", bpfFreq:"~y.linexp(0, 1, 3000, 400)");

~canvas.drawFuncs.removeA(~positionStreams[6])

// ----------------------------------------------- OTHER -------------------------------------------------

// ----------------------------------------------- Overall Actions ---------------------------------------

~heightMaps[0].displayGUI;
~initPositionStreams.value(rate:0.5);
~changeStreamRates.value(1);
~sonifications.freeAll;


// ------------------------------------ INITIALIZATION (Run Once) ------------------------------------------------

(

~heightMaps = [
	HeightMap(200, 200, [
		[0.5, 0.8, 7, 3],
		[0.25, 0.3, 5, 5],
		[0.75, 0.3, 5, 5]
	]);
];

s.waitForBoot({
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
});

~initPositionStreams = {
	|rate=1|
	~positionStreams = [
		PositionStream.new("portrait_1/1_right/datos_13.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_right/datos_15.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_left/datos_16.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_right/datos_17.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_right/datos_18.txt".resolveRelative, dt: 0.002),
		PositionStream.new("portrait_1/1_right/datos_19.txt".resolveRelative, dt: 0.002),
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

Document.globalKeyDownAction = {
	arg document, char, modifiers, unicode, keycode;

	if (modifiers.isCtrl && keycode == 44) { // ctrl+,
		~sonifications.freeAll;
	}
};

thisThread.randSeed = 5;
~streamColors = Array.fill(50, {Color.rand});

~canvas = PositionStream.makeVisualizationCanvas;

~showStreams = { |which=nil|
	which.isNil.if({which = ~positionStreams.size;});
	which.do({ |i|
		~positionStreams[i].visualize(~canvas, showAccel:false, showVelocity:false, dotColor:~streamColors[i % ~streamColors.size]);
	});
};


~hideStreams = { |which=nil|
	which.isNil.if({which = ~positionStreams.size;});
	which.do({ |i|
		~canvas.drawFuncs.removeAt(~positionStreams[i]);
	});
};


~startHarp = {
	|positionStream, scale=(Scale.minorPentatonic), scaleRootFreq=110, numStrings=25,
	pitchHeight="~y", trigRate="~s.linlin(0, 2, 6, 28)", amp="~s.linexp(0, 2, 0.02, 0.2)", pan="~x"|

	{
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
		Out.ar(0, Mix.ar(plucks));
	}.play(target: ~sonifications);
};


~startMapGranulator = {
	|positionStream, sourceMap, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)"|

	{
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
		Out.ar(0, grains);
	}.play(target:~sonifications);
};

~startSines = {
	|positionStream, freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)"|
	{
		var paramIntepreter = positionStream.getParamInterpreter;
		freq = paramIntepreter.(freq);
		vol = paramIntepreter.(vol);
		pan = paramIntepreter.(pan);
		Out.ar(0, Pan2.ar(SinOsc.ar(freq, mul:vol), pan));
	}.play(target:~sonifications);
};

~startWhistle = {
	|positionStream, freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)"|
	{
		var whistle;
		var paramIntepreter = positionStream.getParamInterpreter;
		freq = paramIntepreter.(freq);
		vol = paramIntepreter.(vol);
		pan = paramIntepreter.(pan);
		whistle = BPF.ar(PinkNoise.ar, freq, 0.005, mul:2*vol);
		Out.ar(0, Pan2.ar(whistle, pan));
	}.play(target:~sonifications);
};


~startSaccadeTrigger = {
	|positionStream, soundBuf, rate="~s.linexp(0, 4, 0.5, 1.5)", amp="~s.linexp(0, 4, 0.2, 0.5)", pan="~x.linlin(0, 1, -1, 1)"
	 startTime=0|
	{
		var paramIntepreter = positionStream.getParamInterpreter;
		rate = paramIntepreter.(rate);
		amp = paramIntepreter.(amp);
		pan = paramIntepreter.(pan);
		Out.ar(0, Pan2.ar(
			PlayBuf.ar(soundBuf.numChannels, soundBuf, rate:rate, trigger: positionStream.detectSaccades, startPos: startTime * SampleRate.ir) * amp,
			pan
		));
	}.play(target:~sonifications);
};


~startSimpleGranulator = {
	|positionStream, soundBuf, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)", playRate="1",
	playPos="WhiteNoise.kr(0.5, 0.5)"|

	{
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
		Out.ar(0, grains * amp);
	}.play(target:~sonifications);
};

~startVelTrigger = {
	|positionStream, soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1",
	playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="800"|
	{
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
		Out.ar(0, Pan2.ar(BPF.ar(player * env, bpfFreq), pan));
	}.play(target:~sonifications);
};

~startVelTrigger2 = {
	|positionStream, soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1",
	playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="~y.linexp(0, 1, 3000, 400)", ringFreq="~y.linexp(0, 1, 3000, 400)"|
	{
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
		Out.ar(0, Pan2.ar(BPF.ar(player * env, bpfFreq) * SinOsc.ar(bpfFreq), pan));
	}.play(target:~sonifications);
};

~initPositionStreams.value(rate:0.5);

)

