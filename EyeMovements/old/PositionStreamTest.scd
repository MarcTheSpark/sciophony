(
s.waitForBoot {
	var window, canvas, posX, posY, velX, velY, accelX, accelY;
	var width = 600, height = 600;

	// Load your PositionStream data
	~positionStream = PositionStream.new("fakedata.txt".resolveRelative, dt: 0.01);

	// SynthDef for PositionStream values
	SynthDef(\positionViz, {
		var pos = ~positionStream.pos(0.1);
		var vel = ~positionStream.vel(0.1);
		var accel = ~positionStream.accel(0.1);

		// Send OSC messages with position, velocity, and acceleration
		SendReply.kr(Impulse.kr(30), '/posData', [pos[0], pos[1], vel[0], vel[1], accel[0], accel[1]]);
	}).add;

	s.sync;

	// Start the synth
	~synth = Synth(\positionViz);

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

		// Draw acceleration vector (red)
		Pen.color = Color.red;
		accelVec = dotPos + (Point(accelX, accelY) * 5); // smaller scaling
		Pen.moveTo(dotPos);
		Pen.lineTo(accelVec);
		Pen.stroke;

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