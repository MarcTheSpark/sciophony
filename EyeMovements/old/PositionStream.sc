PSCanvas : UserView {
	var <>drawFuncs;

	*new { |parent, bounds|
		var canvas = super.new(parent, bounds);
		canvas.drawFuncs = Dictionary.new;
		canvas.drawFunc_({
			|view|
			canvas.drawFuncs.keysValuesDo({
				|key, drawFunc|
				drawFunc.value(view);
			});
		});
		^canvas;
	}

}

// PositionStream.sc
PositionStream : Object {
	classvar <>visCounter = 0;
	var <posBufX, <posBufY, <velBufX, <velBufY, <speedBuf, <saccadeBuf, <accelBufX, <accelBufY, <>dt, <numPoints, <>s;
	var <posPhasorBus, <velPhasorBus, <accelPhasorBus, <phasorSynth;
	var initialized;

	*new { |filePath, dt=0.01, s=nil|
		s.isNil.if({s = Server.default});
		^super.new.init(filePath, dt, s);
	}

	init { |filePath, dt, s|
		this.dt = dt;
		this.s = s;
		initialized = Condition.new;
		s.waitForBoot({
			this.loadData(filePath);
			posPhasorBus = Bus.control(s, 1);
			velPhasorBus = Bus.control(s, 1);
			accelPhasorBus = Bus.control(s, 1);
			s.sync;
			initialized.test = true;
			initialized.signal;
		});
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
		var xVel = xNorm.differentiate[1..] / dt;
		var yVel = yNorm.differentiate[1..] / dt;
		var speed = (xVel.pow(2) + yVel.pow(2)).pow(0.5);
		var saccades = PositionStream.findSaccades(speed);
		var xAccel = xVel.differentiate[1..] / dt;
		var yAccel = yVel.differentiate[1..] / dt;

		// Load each dataset into a separate buffer
		posBufX = Buffer.loadCollection(s, xNorm);
		posBufY = Buffer.loadCollection(s, yNorm);
		velBufX = Buffer.loadCollection(s, xVel);
		velBufY = Buffer.loadCollection(s, yVel);
		speedBuf = Buffer.loadCollection(s, speed);
		saccadeBuf = Buffer.loadCollection(s, saccades);
		accelBufX = Buffer.loadCollection(s, xAccel);
		accelBufY = Buffer.loadCollection(s, yAccel);

		numPoints = xNorm.size;
	}

	*findSaccades { |speeds, upperThreshFactor=0.12, lowerThreshFactor=0.04, baselineFraction=0.04|

		var minSpeed, maxSpeed, range, upperThresh, lowerThresh, baselineThresh;
		var saccades, inSaccade;

		saccades = Array.fill(speeds.size, { 0 }); // Initialize with zeros
		inSaccade = false;  // Flag to indicate if we are in a saccade

		// Compute thresholds based on speed range
		minSpeed = speeds.minItem;
		maxSpeed = speeds.maxItem;
		range = maxSpeed - minSpeed;

		upperThresh = minSpeed + (upperThreshFactor * range);
		lowerThresh = minSpeed + (lowerThreshFactor * range);
		baselineThresh = minSpeed + (baselineFraction * range);

		// Main loop to detect saccades with hysteresis and backtracking
		speeds.do { |value, i|
			if ((inSaccade.not).and(value > upperThresh)) {
				// Detected saccade onset, backtrack to refine the onset
				var j = i;
				while { (j >= 0).and(speeds[j] > baselineThresh) } {
					saccades[j] = 1;
					j = j - 1;
				};
				inSaccade = true; // We're now in a saccade
			};

			if (inSaccade) {
				// Mark current position as part of the saccade
				saccades[i] = 1;

				// Check for saccade offset
				if (value < lowerThresh) {
					inSaccade = false; // End of saccade
				};
			};
		};
		^saccades;
	}

	start { |rateMul=1|
		this.stop;
		{
			initialized.wait;
			s.sync;
			phasorSynth = { |rate=1|
				Out.kr(posPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir), 0, numPoints - 1));
				Out.kr(velPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir) * ((numPoints - 1) / numPoints), 0, numPoints - 2));
				Out.kr(accelPhasorBus, Phasor.kr(0, rate / (dt * ControlRate.ir) * ((numPoints - 2) / numPoints), 0, numPoints - 3));
			}.play(target: Group.before(s);, args: [\rate, rateMul]);
		}.fork;
	}

	stop {
		phasorSynth.free;
	}

	changeRate { |rate|
		phasorSynth.set(\rate, rate);
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
	vel { |lag=nil|
		var index = In.kr(velPhasorBus);
		^lag.notNil.if{[
			Lag.kr(BufRd.kr(1, velBufX, index), lag),
			Lag.kr(BufRd.kr(1, velBufY, index), lag)
		]}{[
			BufRd.kr(1, velBufX, index),
			BufRd.kr(1, velBufY, index)
		]};
	}

	speed { |lag=nil|
		var index = In.kr(velPhasorBus);
		^lag.notNil.if{
			Lag.kr(BufRd.kr(1, speedBuf, index), lag);
		}{
			BufRd.kr(1, speedBuf, index);
		};
	}

	detectSaccades {
		var index = In.kr(velPhasorBus);
		^BufRd.kr(1, saccadeBuf, index);
	}

	detectFixations {
		var index = In.kr(velPhasorBus);
		^BinaryOpUGen('==', BufRd.kr(1, saccadeBuf, index), DC.kr(0));
	}

	// Function to stream acceleration using BufRd directly
	accel { |lag=nil|
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
		[posBufX, posBufY, velBufX, velBufY, speedBuf, accelBufX, accelBufY].do(_.free);
	}

	getParamEnvironment { |lag=0.1|
		var pos = this.pos(lag);
		var vel = this.vel(lag);
		var speed = this.speed(lag);
		var accel = this.accel(lag);
		var env = Environment.new(parent:currentEnvironment);
		env.use {
			~x = pos[0]; ~y = pos[1];
			~vx = vel[0]; ~vy = vel[1];
			~ax = accel[0]; ~ay = accel[1];
			~s = speed;
			~ps = this;
		};
		^env;
	}

	getParamInterpreter { |lag=0.1|
		var env = this.getParamEnvironment(lag);
		^{ |paramExpression| env.use{ paramExpression.interpret; }};
	}

	*makeVisualizationCanvas { |width=1000, height=565|
		var window = Window("PositionStream Visualization", Rect(0, 0, width, height)).front;
		^PSCanvas(window, Rect(0, 0, window.bounds.width, window.bounds.height)).animate_(true);
	}

	visualize { |canvas=nil, showAccel=true, showVelocity=true, lag=nil, dotColor=(Color.black), tracelen=30, traceInterpFactor=3|
		// Creates a canvas if needed, and returns it so that it can be passed to other PositionStream visualize calls
		var posX, posY, velX, velY, accelX, accelY, responder;
		var width, height, oldDrawFunc;
		var oscAddress = ('/posData' ++ PositionStream.visCounter).asSymbol;
		var synth;
		var circleLocs = List.new;

		tracelen = tracelen * traceInterpFactor;

		PositionStream.visCounter = PositionStream.visCounter + 1;

		canvas.isNil.if{canvas = PositionStream.makeVisualizationCanvas};

		width = canvas.bounds.width;
		height = canvas.bounds.height;

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

		canvas.drawFuncs.put(this, {
			|view|
			var dotPos, velVec, accelVec;

			// Calculate the position of the dot on the canvas
			dotPos = Point(posX * width, posY * height); // scale and center
			if(circleLocs.size > 0, {
				var interpPoints = Array.fill(traceInterpFactor - 1, { |i|
					var prog = (i + 1) / traceInterpFactor;
					(dotPos * prog) + (circleLocs[0] * (1 - prog));
				});
				interpPoints.do({ |p|
					circleLocs.addFirst(p)
				});
			});
			circleLocs.addFirst(dotPos);
			while({circleLocs.size > tracelen}, {circleLocs.pop;});


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
			circleLocs.reverseDo({ |dp, i|
				Pen.color = Color(dotColor.red, dotColor.green, dotColor.blue, ((1 + i) / tracelen).pow(1.6));
				Pen.fillOval(Rect(dp.x - 5, dp.y - 5, 30, 30));
			});
			Pen.push;
			Pen.width = 2;
			Pen.color = Color.black;
			Pen.strokeOval(Rect(dotPos.x - 5, dotPos.y - 5, 30, 30));
			Pen.pop;
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
			AppClock.sched(0, { canvas.refresh });
		}, oscAddress, s.addr);

		canvas.onClose_({
			// Free the OSCdef when the window is closed
			responder.free;
			synth.free;
		});
		^canvas;
	}

}


HeightMap {
	var <width, <height, <points, <decayFactor, <grid, <buffer, <>s, <normalize;

	// Constructor: Creates the instance, then calls init
	*new { |width, height, points, s=nil, normalize=true|
		s.isNil.if({s = Server.default});
		^super.new.init(width, height, points, s, normalize);
	}

	// Initialize instance variables and compute grid
	init { |w, h, pts, s, norm|
		width = w;
		height = h;
		points = pts; // Array of [x, y, height, decayFactor]
		normalize = norm;
		grid = this.createGrid; // Compute the grid heights
		this.s = s;
		s.waitForBoot({
			buffer = this.asBuffer;
		});
	}


	// Compute the grid heights based on the peaks
	createGrid {
		var grid = Array.fill2D(height, width, {arg r, c; 0;} );

		// Iterate over grid points
		width.do { |x|
			height.do { |y|
				var value = 0.0;
				var xNorm = x / (width - 1);
				var yNorm = y / (height - 1);

				// Add contributions from each peak
				points.do { |peak|
					var px = peak[0];
					var py = peak[1];
					var pHeight = peak[2];
					var decayFactor = peak[3];
					var dist = hypot(px - xNorm, py - yNorm);
					value = value + (pHeight * exp(dist.neg * decayFactor));
				};

				grid[y][x] = value;
			};
		};
		if(normalize, {
			var min = grid.flatten.minItem;
			var max = grid.flatten.maxItem;
			grid = (grid - min) / (max - min);
		});
		^grid
	}

	// Convert the height map to a buffer
	asBuffer {
		var flattened, buf;
		flattened = grid.flatten; // Flatten Array2D to 1D array
		buf = Buffer.sendCollection(s, flattened, 1); // Use sendCollection for brevity
		^buf;
	}

	interp { |x, y, wrapping=false|
		wrapping.if({
			^WaveTerrain.ar(buffer, K2A.ar(x), K2A.ar(y), width, height);
		}, {
			var xScale = (width - 1) / width;
			var yScale = (height - 1) / height;
			^WaveTerrain.ar(buffer, K2A.ar(x.linlin(0, 1, 0, xScale)), K2A.ar(y.linlin(0, 1, 0, yScale)), width, height);
		});
	}

	range {
		var flatgrid = grid.flat;
		^[flatgrid.minItem, flatgrid.maxItem];
	}

	// Debugging: Display the grid row by row
	display {
		height.do { |y|
			var row = (0 .. (width - 1)).collect { |x| grid[y][x].round(0.01) }; // Collect one row
			row.postln; // Print the row
		};
	}

	displayGUI {
		var win, view, maxHeight, minHeight, colors, cellSize;

		win = Window("Height Map", Rect(100, 100, 1000, 1000)).front;
		view = UserView(win, Rect(0, 0, 1000, 1000))
		.background_(Color.black)
		.drawFunc_({
			Pen.translate(0, 0);
			maxHeight = grid.flatten.maxItem;
			minHeight = grid.flatten.minItem;
			cellSize = view.bounds.width / width;

			height.do { |y|
				width.do { |x|
					var normValue = (grid[y][x] - minHeight) / (maxHeight - minHeight + 1e-6);
					var color = Color.hsv(0.66 - (normValue * 0.66), 1, 1); // Blue to red gradient

					Pen.color = color;
					Pen.fillRect(Rect(x * cellSize, y * cellSize, cellSize, cellSize));
				};
			};
		});

		win.onClose_({ view = nil; win = nil; });
		win.front;
	}

}


PositionStreamManager {
	var <>streams, <>canvas, <>streamColors, <>playbackGroup, <>synthsOnStreams, <>oscSender;

	// Constructor: Creates the instance, then calls init
	*new { |streams, canvas=nil, streamColors=nil, playbackGroup=nil, sendOsc=false|
		^super.new.init(streams, canvas, streamColors, playbackGroup, sendOsc);
	}

	// Initialize instance variables and compute grid
	init { |streams, canvas=nil, streamColors=nil, playbackGroup=nil, sendOsc=false|
		canvas.isNil.and(sendOsc.not).if { canvas = PositionStream.makeVisualizationCanvas;};
		streamColors.isNil.if {thisThread.randSeed = 5; streamColors = Array.fill(50, {Color.rand});};
		playbackGroup.isNil.if { playbackGroup = Group.new };
		this.streams = streams;
		this.canvas = canvas;
		this.streamColors = streamColors;
		this.playbackGroup = playbackGroup;
		synthsOnStreams = Dictionary.new;
		sendOsc.if {
			oscSender = NetAddr.new("127.0.0.1", 12000);
		};
	}

	startStreams {
		streams.do{ |stream| stream.start }
	}

	showStreams { |which=nil|
		which.isNil.if({which = streams.size;});
		which.do({ |i|
			this.showStream(i);
		});
	}

	hideStreams { |which=nil|
		which.isNil.if({which = streams.size;});
		which.do({ |i|
			this.hideStream(i);
		});
	}

	showStream { |i|
		canvas.notNil.if {
			streams[i].visualize(canvas, showAccel:false, showVelocity:false, dotColor:streamColors[i % streamColors.size]);
			canvas.front;
		};
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/show", i);
		};
	}

	hideStream { |i|
		canvas.notNil.if {
			canvas.drawFuncs.removeAt(streams[i]);
			canvas.front;
		};
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/hide", i);
		};
	}

	showActiveStreams {
		streams.size.do { |streamNum|
			(synthsOnStreams[streamNum].size > 0).if({
				this.showStream(streamNum);
			}, {
				this.hideStream(streamNum);
			});
		};
	}

	runSonification { |streamNum, sonification|
		var cancellationFunction;
		var synth = sonification.(streams[streamNum]).play(target:playbackGroup);
		synthsOnStreams[streamNum].isNil.if{ synthsOnStreams[streamNum] = List.new; };
		synthsOnStreams[streamNum].add(synth);
		this.showActiveStreams;

		cancellationFunction = {
			synth.free;
			synthsOnStreams[streamNum].remove(synth);
			this.showActiveStreams;
		};
		^cancellationFunction;
	}

	changeRate { |rate|
		streams.do({ |ps|
			ps.changeRate(rate);
		});
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/rate", rate);
		};
	}

}

