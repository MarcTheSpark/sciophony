
Array.fill(20, {2.0.rand - 1}).postln;  // generate coefficients
(
// var xCoefficients =
var xCoefficients = [ 0.86407232284546, -0.62145853042603, 0.22220015525818, 0.21649956703186, -0.25514006614685, -0.30180358886719, -0.01634693145752, 0.65236687660217, 0.59851598739624, -0.84863114356995, -0.40995478630066, 0.013466835021973, -0.58231544494629, 0.046893358230591, -0.15399146080017, -0.83908843994141, -0.12847399711609, 0.80833911895752, -0.62976312637329, -0.83691716194153 ];
var yCoefficients = [ -0.71710634231567, 0.6229932308197, 0.4146728515625, -0.94541692733765, 0.17742538452148, -0.43358087539673, 0.857745885849, 0.027947902679443, 0.1051881313324, -0.96173977851868, 0.38915467262268, -0.47554397583008, 0.14176654815674, 0.02442479133606, 0.35467934608459, -0.33988451957703, 0.72720384597778, -0.4909975528717, -0.28646421432495, -0.016292810440063 ];

var xSig = (Signal.chebyFill(513, xCoefficients) * Signal.welchWindow(513));
var ySig = (Signal.chebyFill(513, yCoefficients) * Signal.welchWindow(513));
var absMax = xSig.abs.maxItem + ySig.abs.maxItem;
~pitchBufX = Buffer.loadCollection(s, xSig/absMax);
~pitchBufY = Buffer.loadCollection(s, xSig/absMax);
~positionStream = PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002);
ySig.plot
)


( // read terrain with mouse
{
	arg pitchRange = #[30, 80];
	var height = BufRd.kr(1, ~pitchBufX, MouseX.kr.linlin(0, 1, 0, BufFrames.ir(~pitchBufX))) + BufRd.kr(1, ~pitchBufY, MouseY.kr.linlin(0, 1, 0, BufFrames.ir(~pitchBufX)));
	height.poll;
	Pulse.ar(height.linlin(-1, 1, pitchRange[0], pitchRange[1]).midicps, mul:0.05);
}.play
)



( // read terrain with eye movements
{
	arg pitchRange = #[30, 80];
	var positionStream = ~positionStream.pos;
	var height = BufRd.kr(1, ~pitchBufX, positionStream[0].linlin(0, 1, 0, BufFrames.ir(~pitchBufX))) + BufRd.kr(1, ~pitchBufY, positionStream[1].linlin(0, 1, 0, BufFrames.ir(~pitchBufX)));
	Pulse.ar(height.linlin(-1, 1, pitchRange[0], pitchRange[1]).midicps, mul:0.05);
}.play;
~positionStream.visualize(lag: 0.005);
)


( // read terrain with eye movements plucked
{
	arg pitchRange = #[30, 85];
	var positionStream = ~positionStream.pos;
	var height = BufRd.kr(1, ~pitchBufX, positionStream[0].linlin(0, 1, 0, BufFrames.ir(~pitchBufX))) + BufRd.kr(1, ~pitchBufY, positionStream[1].linlin(0, 1, 0, BufFrames.ir(~pitchBufX)));
	var freq = height.linlin(-1, 1, pitchRange[0], pitchRange[1]).midicps;
	Pluck.ar(WhiteNoise.ar(0.3), Impulse.kr(20), freq.reciprocal, freq.reciprocal, 10,
        coef:0.5);
}.play;
~positionStream.visualize(lag: 0.005);
)



(  // Harp pluck interactive
var numStrings = 25;
var scale = Scale.choose;
{
	var position = ~positionStream.pos(lag:0.1);
	var velocity = ~positionStream.vel(lag:0.1);
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
~positionStream.visualize(lag: 0.1);

)


(  // Harp pluck non interactive
var numStrings = 25;
var scale = Scale.minorPentatonic;
{
	var rate = 12;
	var mainTrig = Impulse.kr(rate);
	var trigIndex = Demand.kr(mainTrig, 0, Dseq((0..numStrings-1), inf));
	var amp = 0.1;

	var plucks = Array.fill(numStrings, { |i|
		var freq = scale.degreeToFreq(i, 120 , 0);
		var env = Env.new([0,1, 1, 0],[0.001,0.006, 0.0005],[5,-5, -8]);
		var inp = amp * LFClipNoise.ar(2000) * EnvGen.ar(env, mainTrig * BinaryOpUGen('==', trigIndex, i));
		// the LFNoise here creates a fun detuning effect. Try increasing it.
		Pan2.ar(DWGPluckedStiff.ar(freq * LFNoise2.kr(0.1).linexp(-1, 1, 0.99, 1.01), amp, c1:4, c3:20, inp:inp, release:1, fB:80), i.linlin(0, numStrings, -1, 1));
	});

 	Mix.ar(plucks);
}.play
)
