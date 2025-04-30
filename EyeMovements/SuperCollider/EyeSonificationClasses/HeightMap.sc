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