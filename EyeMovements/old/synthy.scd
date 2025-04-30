// Load your PositionStream data
~positionStreamL = PositionStream.new("portrait_1/1_left/datos_7.txt".resolveRelative, dt: 0.004);
~positionStreamR = PositionStream.new("portrait_1/1_right/datos_7.txt".resolveRelative, dt: 0.004);

~positionStreamL.visualize(lag:0.2, showAccel:false);
~positionStreamR.visualize(lag:0.2, showAccel:false);


~positionStreamStartNan = PositionStream.new("portrait_1/1_left/datos_4.txt".resolveRelative, dt: 0.004);
~positionStreamStartNan.visualize(showAccel:false)

(
var rawData = FileReader.read("portrait_1/1_left/datos_4.txt".resolveRelative, skipEmptyLines:true, skipBlanks:true).collect { |tokens|
	[tokens[1].asFloat, tokens[2].asFloat]  // x, y positions
};
var xRaw = all{:k[0], k <- rawData}, yRaw = all{:k[1], k <- rawData};
var xMin = xRaw.minItem, yMin = yRaw.minItem;
var xMax = xRaw.maxItem, yMax = yRaw.maxItem;
var xNorm = (xRaw - xMin) / (xMax - xMin);
var yNorm = (yRaw - yMin) / (yMax - yMin);
xRaw[3]
)

x / [[10, 1000]]

(
var rawData = FileReader.read("portrait_1/1_left/datos_4.txt".resolveRelative, skipEmptyLines:true, skipBlanks:true).collect { |tokens|
	[tokens[1].asFloat, tokens[2].asFloat]  // x, y positions
};
var xRaw = all{:k[0], k <- rawData}, yRaw = all{:k[1], k <- rawData};
~nan = xRaw[0];
PositionStream.interpolateNaN([~nan, ~nan, 5, 7, 8, 9, ~nan, 7, ~nan, ~nan, ~nan, 6, ~nan, ~nan, ~nan])
)


Number..isNaN


(5..7)