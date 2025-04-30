(
~positionStream = PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002);
~positionStream2 = PositionStream.new("portrait_1/1_left/datos_16.txt".resolveRelative, dt: 0.002);
~positionStream.start(0.5);
~positionStream2.start(0.5);
~sonifications = Group.new;
)

~sonifications.freeAll;

(
~canvas  = ~positionStream.visualize(showAccel:false, showVelocity:false);
~positionStream2.visualize(~canvas, showAccel:false, showVelocity:false);
)


~puff = Buffer.read(s, "puff.wav".resolveRelative)
x = ~puff.play
//
x = {PlayBuf.ar(1, ~puff, ~positionStream.speed/5, ~positionStream.detectSaccades) ! 2}.play
x.free
( // saccade test
{
	//Out.ar(0, WhiteNoise.ar(0.03) ! 2 * ~positionStream.detectSaccades);
	Out.ar(0, SinOsc.ar(400 + (~positionStream.speed * 100), mul:0.03) ! 2 * ~positionStream.detectFixations);
}.play;
)

( // saccade test
~positionStream.visualize(showAccel:false);
{
	var fixationMask = ~positionStream.detectFixations.lag(0.1);
	var saccadeMask = ~positionStream.detectSaccades.lag(0.05);
	Out.ar(0, WhiteNoise.ar(0.03) ! 2 * saccadeMask);
	Out.ar(0, SinOsc.ar(400 + (~positionStream.speed * 10), mul:0.03) ! 2 * fixationMask);
}.play(target:~sonifications);
)



(
{
	var positionStream = ~positionStream2;
	// Load buffers for sources
	~sources = [
		Dictionary[
			\location -> [0.5, 0.9],
			\buf -> Buffer.read(s, "xylophoneOneNote.wav".resolveRelative),
			\sourceRange -> [0.2, 0.8]
		],
		Dictionary[
			\location -> [0.5, 0.1],s
			\buf -> Buffer.read(s, "waterpipe.wav".resolveRelative),
			\sourceRange -> [0, 1]
		]
	];

	s.sync;

	SynthDef(\positionGranulator, {
		|rate = 30, amp = 0.2, dur = 0.05, pan = 0|

		var pos = positionStream.pos(0.1);
		var vel = positionStream.vel(0.1);
		var accel = positionStream.accel(0.1);

		var speed = ((vel[0] * vel[0]) + (vel[1] * vel[1])).sqrt;

		// Calculate distances to each source location
		var distances = ~sources.collect { |src|
			var locX = src[\location][0];
			var locY = src[\location][1];
			hypot(pos[0] - locX, pos[1] - locY) // Euclidean distance
		};

		// Invert distances to create probabilities (closer distance -> higher probability)
		var invDistances = distances.collect { |dist| 1 / (dist + 0.001) }; // Small offset to avoid division by zero

		// Normalize the inverted distances to sum to 1
		var total = invDistances.sum;
		var volumes = (invDistances / total).pow(1.5) * 2;

		// Main trigger
		var mainTrig = Impulse.kr(rate);

		// Create grains for each buffer, modulating their amplitudes based on distance
		var grains = Mix(~sources.collect { |src, i|
			GrainBuf.ar(2, mainTrig, dur, src[\buf].bufnum, pos[0].linexp(0, 1, 1.1, 1.6), WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]), 2, pos[0] * 2 - 1) * volumes[i] * speed.min(4).max(0.3);
		});

		// Send OSC messages with position, velocity, and acceleration
		SendReply.kr(Impulse.kr(30), '/posData', [pos[0], pos[1], vel[0], vel[1], accel[0], accel[1]]);

		// Output the mixed grains, scaled by amp
		Out.ar(0, grains * amp);
	}).add;

	s.sync;

	// Start the synth
	~synth = Synth(\positionGranulator, target:~sonifications);
}.fork;
)

(
var rate = 1;
~positionStream.changeRate(rate);
~positionStream2.changeRate(rate);
)


(
{
	[
		SinOsc.ar(~positionStream.pos()[0].linexp(0, 1, 220, 1760) + (~positionStream.speed * 100), mul:0.05),
		SinOsc.ar(~positionStream.pos()[1].linexp(0, 1, 220, 1760) + (~positionStream.speed * 100), mul:0.05),
	]
}.play(target:~sonifications);
{
	[
		SinOsc.ar(~positionStream2.pos()[0].linexp(0, 1, 220, 1760) + (~positionStream2.speed * 100), mul:0.05),
		SinOsc.ar(~positionStream2.pos()[1].linexp(0, 1, 220, 1760) + (~positionStream2.speed * 100), mul:0.05),
	]
}.play(target:~sonifications);
)



(
// var xCoefficients =
var xCoefficients = [ 0.86407232284546, -0.62145853042603, 0.22220015525818, 0.21649956703186, -0.25514006614685, -0.30180358886719, -0.01634693145752, 0.65236687660217, 0.59851598739624, -0.84863114356995, -0.40995478630066, 0.013466835021973, -0.58231544494629, 0.046893358230591, -0.15399146080017, -0.83908843994141, -0.12847399711609, 0.80833911895752, -0.62976312637329, -0.83691716194153 ];
var yCoefficients = [ -0.71710634231567, 0.6229932308197, 0.4146728515625, -0.94541692733765, 0.17742538452148, -0.43358087539673, 0.857745885849, 0.027947902679443, 0.1051881313324, -0.96173977851868, 0.38915467262268, -0.47554397583008, 0.14176654815674, 0.02442479133606, 0.35467934608459, -0.33988451957703, 0.72720384597778, -0.4909975528717, -0.28646421432495, -0.016292810440063 ];

var xSig = (Signal.chebyFill(513, xCoefficients) * Signal.welchWindow(513));
var ySig = (Signal.chebyFill(513, yCoefficients) * Signal.welchWindow(513));
var absMax = xSig.abs.maxItem + ySig.abs.maxItem;
~pitchBufX = Buffer.loadCollection(s, xSig/absMax);
~pitchBufY = Buffer.loadCollection(s, xSig/absMax);
ySig.plot
)

(  // Harp pluck interactive
var numStrings = 25;
var scale = Scale.choose;
{
	var position = ~positionStream.pos;
	var velocity = ~positionStream.vel;
	var speed = hypot(velocity[0], velocity[1]);
	var height = BufRd.kr(1, ~pitchBufX, position[0].linlin(0, 1, 0, BufFrames.ir(~pitchBufX))) + BufRd.kr(1, ~pitchBufY, position[1].linlin(0, 1, 0, BufFrames.ir(~pitchBufX)));
	var rate = 12;
	var mainTrig = Impulse.kr(speed.lag(0.05).linexp(0, 2, 12, 50));
	var trigIndex = height.linlin(-1, 1, 0, numStrings).round;
	var amp = speed.linlin(0, 2, 0.03, 0.08);

	var plucks = Array.fill(numStrings, { |i|
		var freq = scale.degreeToFreq(i, 120 , 0);
		var env = Env.new([0,1, 1, 0],[0.001,0.006, 0.0005],[5,-5, -8]);
		var inp = amp * LFClipNoise.ar(2000) * EnvGen.ar(env, mainTrig * BinaryOpUGen('==', trigIndex, i));
		// the LFNoise here creates a fun detuning effect. Try increasing it.
		Pan2.ar(DWGPluckedStiff.ar(freq * LFNoise2.kr(0.1).linexp(-1, 1, 0.99, 1.01), amp, c1:4, c3:20, inp:inp, release:1, fB:80), i.linlin(0, numStrings, -1, 1));
	});
 	Mix.ar(plucks);
}.play;

)


// Incorporate pitch map

~positionStream = PositionStream.new("fakedata.txt".resolveRelative);
CSVFileReader.read("fakedata.txt".resolveRelative)
~positionStream.pos

// Decaying air sound?

// Finish Height Map
// Distance between two position streams
// More musical sounds
// peaceful and hypnotic; doesn't require a lot of attention and fatigue
// Differentiating between observers by encoding identity of observer by having fixed parameters for those observers (pull out paramters from synthdef)
// Touching a paper with a brush: ideally working with the pressure of the stroke (pressure the inverse of velocity?)
// Draw a shadow/trail behind the eyes
// freeing the synths better
// ##Crescendo during fixation from silence to loud; could be tinkly sound to start with
// BRUSH + WATER
// Make it as a bunch of sonifications that can be layered on one another
// Make it easy to change how many observers there are