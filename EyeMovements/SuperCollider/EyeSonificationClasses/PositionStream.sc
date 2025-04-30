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
	var <posBufX, <posBufY, <velBufX, <velBufY, <speedBuf, <saccadeBuf, <accelBufX, <accelBufY, <>dt, <numPoints, <duration, <>s;
	var <>timingBus;

	*new { |filePath, timingBus, s, dt=0.01, rect=nil|
		^super.new.init(filePath, timingBus, s, dt, rect);
	}

	init { |filePath, timingBus, s, dt, rect|
		this.s = s;
		this.dt = dt;
		this.timingBus = timingBus;
		this.loadData(filePath, rect);
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

	loadData { |filePath, rect|
		// Read and parse x, y data from the file
		var rawData = FileReader.read(filePath.resolveRelative, skipEmptyLines:true, skipBlanks:true).collect { |tokens|
			[tokens[1].asFloat, tokens[2].asFloat]  // x, y positions
		};
		var xRaw = PositionStream.interpolateNaN(all{:k[0], k <- rawData}), yRaw = PositionStream.interpolateNaN(all{:k[1], k <- rawData});
		var xMin = rect.isNil.if{xRaw.minItem}{rect.left}, yMin = rect.isNil.if{yRaw.minItem}{rect.top};
		var xMax = rect.isNil.if{xRaw.maxItem}{rect.right}, yMax = rect.isNil.if{yRaw.maxItem}{rect.bottom};
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
		duration = numPoints * dt;
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

	// Function to stream position using BufRd directly
	pos { |lag=nil|
		var index = (In.kr(timingBus) % duration) * (posBufX.numFrames / duration);
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
		var index = (In.kr(timingBus) % duration) * (velBufX.numFrames / duration);
		^lag.notNil.if{[
			Lag.kr(BufRd.kr(1, velBufX, index), lag),
			Lag.kr(BufRd.kr(1, velBufY, index), lag)
		]}{[
			BufRd.kr(1, velBufX, index),
			BufRd.kr(1, velBufY, index)
		]};
	}

	speed { |lag=nil|
		var index = (In.kr(timingBus) % duration) * (speedBuf.numFrames / duration);
		^lag.notNil.if{
			Lag.kr(BufRd.kr(1, speedBuf, index), lag);
		}{
			BufRd.kr(1, speedBuf, index);
		};
	}

	detectSaccades {
		var index = (In.kr(timingBus) % duration) * (saccadeBuf.numFrames / duration);
		^BufRd.kr(1, saccadeBuf, index);
	}

	detectFixations {
		var index = (In.kr(timingBus) % duration) * (saccadeBuf.numFrames / duration);
		^BinaryOpUGen('==', BufRd.kr(1, saccadeBuf, index), DC.kr(0));
	}

	// Function to stream acceleration using BufRd directly
	accel { |lag=nil|
		var index = (In.kr(timingBus) % duration) * (accelBufX.numFrames / duration);
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

	*makeVisualizationCanvas { |width=565, height=1000|
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

PositionStreamGroup {
	var <>streams, <>canvas, <>streamColors, <>playbackGroup, <>synthsOnStreams, <>streamShown, <>oscSender, <>s;
	var <>timingBus, timingSynth, <rate;
	var initialized;

	// Constructor: Creates the instance, then calls init
	*new { |streamPaths, playbackGroup=nil, canvas=nil, sendOsc=false, streamColors=nil, s=nil, streamDt=0.002, startRate=1, streamsRect=nil|
		s.isNil.if({s = Server.default});
		^super.new.init(streamPaths, playbackGroup, canvas, sendOsc, streamColors, s, streamDt, startRate, streamsRect);
	}

	// Initialize instance variables and compute grid
	init { |streamPaths, playbackGroup=nil, canvas=nil, sendOsc=false, streamColors=nil, s, streamDt=0.002, startRate=1.0, streamsRect=nil|
		canvas.isNil.and(sendOsc.not).if { canvas = PositionStream.makeVisualizationCanvas;};
		streamColors.isNil.if {thisThread.randSeed = 5; streamColors = Array.fill(50, {Color.rand});};
		this.s = s;
		this.canvas = canvas;
		this.streamColors = streamColors;
		this.rate = startRate;
		initialized = Condition.new;
		synthsOnStreams = Array.fill(streamPaths.size, { List.new });
		streamShown = Array.fill(streamPaths.size, { false });
		sendOsc.if {
			oscSender = NetAddr.new("127.0.0.1", 12000);
		};
		s.waitForBoot {
			this.playbackGroup = playbackGroup.isNil.if { playbackGroup = Group.new } {playbackGroup};
			timingBus = Bus.control(s);
			s.sync;
			this.streams = streamPaths.collect {
				|path|
				var stream = PositionStream(path, timingBus, s, streamDt, streamsRect);
				s.sync;
				stream;
			};
			initialized.test = true;
			initialized.signal;
		}
	}

	start {
		initialized.wait;
		timingSynth.free;
		{
			timingSynth = {
				|rate=1|
				var timeSweep = Sweep.kr(rate:rate);
				SendReply.kr(Impulse.kr(2), '/timer', timeSweep);
				Out.kr(timingBus, timeSweep);
			}.play;
			s.sync;
			timingSynth.set(\rate, rate);
			oscSender.notNil.if {
				OSCdef(\timeListener, {|msg|
					var time = msg[3];
					oscSender.sendMsg("/eyes/setTime", time);
					oscSender.sendMsg("/eyes/rate", rate);
				}, '/timer');

			};

		}.fork;
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/setTime", 0.0);
			oscSender.sendMsg("/eyes/rate", rate);
		};
	}

	killSonifications { |whichStreams=nil, hard=false|
		whichStreams.isNil.if({whichStreams = streams.size;});
		whichStreams.do({ |i|
			this.hideStream(i);
			this.synthsOnStreams[i].do { |synth| hard.if {synth.free;} {synth.set(\gate, 0;)} };
			this.synthsOnStreams[i].clear;
		});

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
		streamShown[i].if{^false};
		canvas.notNil.if {
			AppClock.sched(0, {
			streams[i].visualize(canvas, showAccel:false, showVelocity:false, dotColor:streamColors[i % streamColors.size]);
			});
			canvas.front;
		};
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/show", i);
		};
		streamShown[i] = true;
	}

	hideStream { |i|
		streamShown[i].not.if{^false};
		canvas.notNil.if {
			canvas.drawFuncs.removeAt(streams[i]);
			canvas.front;
		};
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/hide", i);
		};
		streamShown[i] = false;
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

	runSonification { |streamNum, sonification, onCancel=nil|
		var cancellationFunction;
		var synth = sonification.(streams[streamNum]).play(target:playbackGroup);
		synth.onFree(onCancel);
		synthsOnStreams[streamNum].add(synth);
		this.showActiveStreams;

		cancellationFunction = { |hard=false|
			hard.if {synth.free;} {synth.set(\gate, 0;)};
			synthsOnStreams[streamNum].remove(synth);
			this.showActiveStreams;
		};
		^cancellationFunction;
	}


	setDrawMethod { |which|
		// only applicable for OSC to processing!
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/drawMethod", which);
		};
	}

	rate_ { |value|
		rate = value.asFloat;
		timingSynth.set(\rate, rate);
		oscSender.notNil.if {
			oscSender.sendMsg("/eyes/rate", rate);
		};
	}

}
