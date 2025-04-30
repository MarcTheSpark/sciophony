(

s.waitForBoot {
	var window, canvas, posX, posY, velX, velY, accelX, accelY;
	var width = 600, height = 600;

	// Load your PositionStream data
	// ~positionStream = PositionStream.new("fakedata.txt".resolveRelative, dt: 0.01);
	~positionStream = PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002);

	// Load buffers for sources
	~sources = [
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
	];

	s.sync;

	SynthDef(\positionGranulator, {
		|rate = 30, amp = 0.2, dur = 0.05, pan = 0|

		var pos = ~positionStream.pos(0.1);
		var vel = ~positionStream.vel(0.1);
		var accel = ~positionStream.accel(0.1);

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
			GrainBuf.ar(2, mainTrig, dur, src[\buf].bufnum, pos[0].linexp(0, 1, 0.7, 1.3), WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]), 2, pos[0] * 2 - 1) * volumes[i] * speed.min(4).max(0.3);
		});

		speed.poll;
		// Send OSC messages with position, velocity, and acceleration
		SendReply.kr(Impulse.kr(30), '/posData', [pos[0], pos[1], vel[0], vel[1], accel[0], accel[1]]);

		// Output the mixed grains, scaled by amp
		Out.ar(0, grains * amp);
	}).add;

	s.sync;

	// Start the synth
	~synth = Synth(\positionGranulator);

	// Initialize position and vector values
	posX = posY = velX = velY = accelX = accelY = 0;

	// Create window and canvas
	window = Window("Position Visualization", Rect(200, 200, width, height)).front;
	canvas = UserView(window, Rect(0, 0, 600, 600))
	.background_(Color.white)
	.animate_(true) // Enable continuous drawing
	.drawFunc_({
		|view|
		var dotPos, velVec, accelVec;

		// Calculate position of the dot
		dotPos = Point(posX * width, posY * height); // scale and center

		// Set up Pen for drawing
		Pen.width = 3;

		// Draw velocity vector (blue)
		Pen.color = Color.blue;
		velVec = dotPos + (Point(velX, velY) * 100); // scale for visibility
		Pen.moveTo(dotPos);
		Pen.lineTo(velVec);
		Pen.stroke;

		/*// Draw acceleration vector (red)
		Pen.color = Color.red;
		accelVec = dotPos + (Point(accelX, accelY) * 5); // smaller scaling
		Pen.moveTo(dotPos);
		Pen.lineTo(accelVec);
		Pen.stroke;*/

		// Draw the moving dot (black)
		Pen.color = Color.black;
		Pen.fillOval(Rect(dotPos.x - 5, dotPos.y - 5, 10, 10));
	});

	// OSC responder to receive position, velocity, and acceleration
	OSCdef(\posData, {
		|msg|
		posX = msg[3];
		posY = msg[4];
		velX = msg[5];
		velY = msg[6];
		accelX = msg[7];
		accelY = msg[8];
		AppClock.sched(0, {canvas.refresh});
	}, '/posData', s.addr);
};
)



(
{
	~positionStream = PositionStream.new("portrait_1/1_right/datos_14.txt".resolveRelative, dt: 0.002);
	~positionStream2 = PositionStream.new("portrait_1/1_left/datos_14.txt".resolveRelative, dt: 0.002);
	s.waitForBoot({
		~positionStream.start(0.2);
		~positionStream2.start(0.2);
	});
}.fork;

)
~canvas  = ~positionStream.visualize(showAccel:false)
~positionStream2.visualize(~canvas, showAccel:false)

(
var rate = 1;
~positionStream.changeRate(rate);
~positionStream2.changeRate(rate);
)

{
	[
		SinOsc.ar(~positionStream.pos(rateMul:0.1)[0].linexp(0, 1, 220, 1760), mul:0.05),
		SinOsc.ar(~positionStream.pos(rateMul:0.1)[1].linexp(0, 1, 220, 1760), mul:0.05),
	]
}.play;



~positionStream.start; ~positionStream2.start;
~positionStream.stop
~positionStream.changeRate(1)
{In.kr(~position.Stream.posPhasorBus).poll}.play
(
var win = ~positionStream.visualize(showAccel:false);
~positionStream2.visualize(win, showAccel:false);

{
	[
		SinOsc.ar(~positionStream.pos(rateMul:0.1)[0].linexp(0, 1, 220, 1760), mul:0.05),
		SinOsc.ar(~positionStream.pos(rateMul:0.1)[1].linexp(0, 1, 220, 1760), mul:0.05),
	]
}.play;
{
	[
		SinOsc.ar(~positionStream2.pos(rateMul:0.1)[0].linexp(0, 1, 220, 1760), mul:0.05),
		SinOsc.ar(~positionStream2.pos(rateMul:0.1)[1].linexp(0, 1, 220, 1760), mul:0.05),
	]
}.play;
)

// fixations, sensing data interspersed with jumps
// Maybe cicades are sonified in a different way? Different sound?
// Somehow filtering out the cicades from the fixations so that they are sonified differently
// look for algorithm to detect cicades
// Incorporate pitch map
// Work on making it easy to sync different layers. Overlap. Orchestrate. Easier to fork them on top of each other. X
// More observations on one canvas


~positionStream = PositionStream.new("fakedata.txt".resolveRelative);
CSVFileReader.read("fakedata.txt".resolveRelative)
~positionStream.pos
