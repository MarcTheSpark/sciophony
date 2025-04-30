// PositionStream.sc
PositionStream : Object {
	classvar <instanceCounter = 0;
	var <posBufX, <posBufY, <velBufX, <velBufY, <accelBufX, <accelBufY, <>dt, <numPoints, <>s;
	var <posPhasorBus, <velPhasorBus, <accelPhasorBus, <phasorSynth;
	var <posX, <posY, <velX, <velY, <accelX, <accelY, <monitorSynth, <monitorResponder, <monitoringOSCAddress;

	*new { |filePath, dt=0.01, s=nil|
		s.isNil.if({s = Server.default});
		^super.new.init(filePath, dt, s);
	}

	init { |filePath, dt, s|
		this.dt = dt;
		this.s = s;
		s.waitForBoot({
			this.loadData(filePath);
			posPhasorBus = Bus.control(s, 1);
			velPhasorBus = Bus.control(s, 1);
			accelPhasorBus = Bus.control(s, 1);
		})
		var monitoringOSCAddress = ('/posData' ++ PositionStream.instanceCounter).asSymbol;
	}

	*interpolateNaN { |dataArray|
		var cleanData = dataArray.copy;

		// Handle initial NaN values by setting them to the first non-NaN value
		var firstValidIdx = cleanData.detectIndex { |val| val.isNaN.not };

		firstValidIdx.notNil.if {
			cleanData.do { |val, idx|
				if (idx < firstValidIdx) {
					cleanData[idx] = cleanData[firstValidIdx];
				}
			};
		};

		// fill in NaNs with previous values
		cleanData.do { |val, idx|
			if (val.isNaN) {
				cleanData[idx] = cleanData[(idx - 1).max(0)];
			};
		};

		^cleanData;
	}

	loadData { |filePath|
		// Read and parse x, y data from the file
		var rawData = FileReader.read(filePath.resolveRelative, skipEmptyLines:true, skipBlanks:true).collect { |tokens|
			[tokens[1].asFloat, tokens[2].asFloat]  // x, y positions
		};
		var xRaw = PositionStream.interpolateNaN(all{:k[0], k <- rawData}), yRaw = PositionStream.interpolateNaN(all{:k[1], k <- rawData});
		var xMin = xRaw.minItem, yMin = yRaw.minItem;
		var xMax = xRaw.maxItem, yMax = yRaw.maxItem;
		var xNorm = (xRaw - xMin) / (xMax - xMin);
		var yNorm = (yRaw - yMin) / (yMax - yMin);

		// Calculate velocity and acceleration
		var xVel = xNorm.differentiate / dt;
		var yVel = yNorm.differentiate / dt;
		var xAccel = xVel.differentiate / dt;
		var yAccel = yVel.differentiate / dt;

		// Load each dataset into a separate buffer
		posBufX = Buffer.loadCollection(s, xNorm);
		posBufY = Buffer.loadCollection(s, yNorm);
		velBufX = Buffer.loadCollection(s, xVel);
		velBufY = Buffer.loadCollection(s, yVel);
		accelBufX = Buffer.loadCollection(s, xAccel);
		accelBufY = Buffer.loadCollection(s, yAccel);

		numPoints = xNorm.size;
	}

	start { |rateMul=1|
		this.stop;
		phasorSynth = { |rate=1|
			Out.kr(posPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir), 0, numPoints - 1));
			Out.kr(velPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir) * ((numPoints - 1) / numPoints), 0, numPoints - 2));
			Out.kr(accelPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir) * ((numPoints - 2) / numPoints), 0, numPoints - 3));
		}.play(args: [\rate, rateMul]);
	}

	stop {
		phasorSynth.free;
	}

	changeRate { |rate|
		phasorSynth.set(\rate, rate);
	}

	monitor {
		monitorSynth = {
			var pos = this.pos(lag);
			var vel = this.vel(lag);
			var accel = this.accel(lag);

			// Send OSC messages with position, velocity, and acceleration data
			SendReply.kr(Impulse.kr(30), oscAddress, [pos[0], pos[1], vel[0], vel[1], accel[0], accel[1]]);
		}.play;
		monitorResponder = OSCdef(oscAddress, {
			|msg|
			posX = msg[3];
			posY = msg[4];
			velX = msg[5];
			velY = msg[6];
			accelX = msg[7];
			accelY = msg[8];
		}, oscAddress, s.addr);
	}

	// Function to stream position using BufRd directly
	pos { |lag=nil|
		var index = In.kr(posPhasorBus); // Increment index based on dt
		^lag.notNil.if{[
			Lag.kr(BufRd.kr(1, posBufX, index), lag),
			Lag.kr(BufRd.kr(1, posBufY, index), lag)
		]}{[
			BufRd.kr(1, posBufX, index),
			BufRd.kr(1, posBufY, index)
		]};
	}

	// Function to stream velocity using BufRd directly
	vel { |lag=nil, rateMul=1|
		var index = In.kr(velPhasorBus);
		^lag.notNil.if{[
			Lag.kr(BufRd.kr(1, velBufX, index), lag),
			Lag.kr(BufRd.kr(1, velBufY, index), lag)
		]}{[
			BufRd.kr(1, velBufX, index),
			BufRd.kr(1, velBufY, index)
		]};
	}

	// Function to stream acceleration using BufRd directly
	accel { |lag=nil, rateMul=1|
		var index = In.kr(accelPhasorBus);
		^lag.notNil.if{[
			Lag.kr(BufRd.kr(1, accelBufX, index), lag),
			Lag.kr(BufRd.kr(1, accelBufY, index), lag)
		]}{[
			BufRd.kr(1, accelBufX, index),
			BufRd.kr(1, accelBufY, index)
		]};
	}

	free {
		[posBufX, posBufY, velBufX, velBufY, accelBufX, accelBufY].do(_.free);
	}

	visualize { |window=nil, showAccel=true, showVelocity=true, lag=nil|
		// Creates a canvas if needed, and returns it so that it can be passed to other PositionStream visualize calls
		var posX, posY, velX, velY, accelX, accelY, responder;
		var width, height, oldDrawFunc;
		var oscAddress = ('/posData' ++ PositionStream.instanceCounter).asSymbol;
		var synth;
		var canvas;

		window.isNil.if({
			window = Window("PositionStream Visualization", Rect(0, 0, 800, 800)).front;
		});
		width = window.bounds.width;
		height = window.bounds.height;
		canvas = UserView(window, Rect(0, 0, width, height)).animate_(true);

		// Start the synth
		synth = {
			var pos = this.pos(lag);
			var vel = this.vel(lag);
			var accel = this.accel(lag);

			// Send OSC messages with position, velocity, and acceleration data
			SendReply.kr(Impulse.kr(30), oscAddress, [pos[0], pos[1], vel[0], vel[1], accel[0], accel[1]]);
		}.play;

		// Initialize position and vector values
		posX = posY = velX = velY = accelX = accelY = 0;

		canvas.drawFunc_({
			|view|
			var dotPos, velVec, accelVec;

			// Calculate the position of the dot on the canvas
			dotPos = Point(posX * width, posY * height); // scale and center

			// Set up Pen for drawing
			Pen.width = 3;

			// Draw velocity vector if enabled
			if (showVelocity) {
				Pen.color = Color.blue;
				velVec = dotPos + (Point(velX, velY) * 100); // scale for visibility
				Pen.moveTo(dotPos);
				Pen.lineTo(velVec);
				Pen.stroke;
			};

			// Draw acceleration vector if enabled
			if (showAccel) {
				Pen.color = Color.red;
				accelVec = dotPos + (Point(accelX, accelY) * 5); // smaller scaling
				Pen.moveTo(dotPos);
				Pen.lineTo(accelVec);
				Pen.stroke;
			};

			// Draw the moving dot
			Pen.color = Color.black;
			Pen.fillOval(Rect(dotPos.x - 5, dotPos.y - 5, 10, 10));
		});


		// OSC responder to update position, velocity, and acceleration values
		responder = OSCdef(oscAddress, {
			|msg|
			posX = msg[3];
			posY = msg[4];
			velX = msg[5];
			velY = msg[6];
			accelX = msg[7];
			accelY = msg[8];
		}, oscAddress, s.addr);

		canvas.onClose_({
			// Free the OSCdef when the window is closed
			responder.free;
			synth.free;
		});
		^canvas;
	}

}

/*
This doesn't seem to be working the way I want. I'd like you to rework it so that there is a PositionStreamVisualizer class, which inherits from the Window class, and which maintains a list of PositionStreams to visualize, and Dictionary keeping track of the current position, velocity and acceleration of each of those PositionStreams. It should have an add and a remove method for PositionStreams, When you add a stream, it spawns a synth and osc listener that like the one in the above code
*/