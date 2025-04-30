(
// Load buffers for sources
~sources = [
    Dictionary[
        \location -> [0.2, 0.7],
        \buf -> Buffer.read(s, "xylophoneOneNote.wav".resolveRelative),
        \sourceRange -> [0.2, 0.8]
    ],
    Dictionary[
        \location -> [0.4, 0.5],
        \buf -> Buffer.read(s, "waterpipe.wav".resolveRelative),
        \sourceRange -> [0, 1]
    ]
];
)

(
SynthDef(\distanceGrainSelector, {
	|rate = 30, amp = 0.2, dur = 0.05, pan = 0|

    // Mouse location in the range 0 to 1
    var mouseX = MouseX.kr(0, 1);
    var mouseY = MouseY.kr(0, 1);

    // Calculate distances to each source location
    var distances = ~sources.collect { |src|
        var locX = src[\location][0];
        var locY = src[\location][1];
        hypot(mouseX - locX, mouseY - locY) // Euclidean distance
    };

    // Invert distances to create probabilities (closer distance -> higher probability)
    var invDistances = distances.collect { |dist| 1 / (dist + 0.001) }; // Small offset to avoid division by zero

    // Normalize the inverted distances to sum to 1
    var total = invDistances.sum;
	var volumes = invDistances / total;

    // Main trigger
    var mainTrig = Impulse.kr(rate);

    // Create grains for each buffer, modulating their amplitudes based on distance
    var grains = Mix(~sources.collect { |src, i|
		GrainBuf.ar(2, mainTrig, dur, src[\buf].bufnum, 1, WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]), 2, pan) * volumes[i]
    });

    // Output the mixed grains, scaled by amp
    Out.ar(0, grains * amp);
}).play;
)


~positionStream = PositionStream.new("fakedata.txt".resolveRelative);
CSVFileReader.read("fakedata.txt".resolveRelative)
~positionStream.pos
{~positionStream.pos[0]}.play