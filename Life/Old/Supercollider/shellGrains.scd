MarcUtilities.setOutputLimiter(0.3, 0.3)



(
var winenv = Env([1, 0], [1.0], [-3]);
var tileWidth = 36;
var tileHeight = 36;
var numTiles = tileWidth * tileHeight;

b = Buffer.read(s, "shellsCompressedFiltered.wav".resolveRelative);
// a custom envelope
z = Buffer.sendCollection(s, winenv.discretize, 1);

SynthDef(\shellGrains, { |out, gate = 1, volume = 1, sndbuf, envbuf|
    var panIndex, pan, filter, trig, env, granulated;
	var activity = NamedControl.kr(\activities, Array.fill(tileWidth, {0}));  // distribution of activity from left to right
	var averageHeights = NamedControl.kr(\averageHeights, Array.fill(tileWidth, {|i| tileHeight / 2}));
	var activityPercent = activity.sum / numTiles;
	trig = Impulse.kr(activityPercent.explin(0.01, 1, 3, 100));
	panIndex = TWindex.kr(trig, activity, normalize: 1);
	pan = Select.kr(panIndex, Array.fill(36, {|i| i.linlin(0, 35, -1, 1)}));
	filter = Select.kr(panIndex, averageHeights).linlin(0, tileHeight,0, 1);
	granulated = GrainBuf.ar(
		2, trig, 0.25, sndbuf, filter.linexp(0, 1, 0.6, 1.5), WhiteNoise.kr(mul:0.2, add:filter*0.8 + 0.1), 2,
		pan,
		envbuf);

	Out.ar(out,granulated * EnvFollow.ar(K2A.ar(Select.kr(panIndex, activity).linlin(0, tileHeight,0, 4))) * EnvGate(volume, gate));
}).add;

OSCFunc.newMatching({|msg, time, addr, recvPort| x = Synth(\shellGrains, [\sndbuf, b, \envbuf, z])}, '/shells/start');
OSCFunc.newMatching({|msg, time, addr, recvPort| x.setn(\activities, msg[1..])}, '/shells/activity');
OSCFunc.newMatching({|msg, time, addr, recvPort| x.setn(\averageHeights, msg[1..])}, '/shells/heights');
OSCFunc.newMatching({|msg, time, addr, recvPort| x.set(\gate, 0)}, '/shells/stop');

)


//
// (
// var winenv;
//
// b = Buffer.read(s, "shellsCompressedFiltered.wav".resolveRelative);
// // a custom envelope
// winenv = Env([1, 0], [1.0], [-3]);
// z = Buffer.sendCollection(s, winenv.discretize, 1);
//
// SynthDef(\buf_grain_test, { |out, gate = 1, volume = 1, sndbuf, envbuf|
// 	var pan, filter, env, granulated;
// 	// use mouse x to control panning
// 	pan = MouseX.kr(-1, 1);
// 	filter = MouseY.kr(0, 1);
// 	granulated = GrainBuf.ar(2, Impulse.kr(30), 0.3, sndbuf, filter.linexp(0, 1, 0.6, 1.5), WhiteNoise.kr(mul:0.2, add:filter*0.8 + 0.1), 2, pan, envbuf);
// 	Out.ar(out,granulated * EnvGate(volume, gate));
// }).add;
// )
//
// x = Synth(\buf_grain_test, [\sndbuf, b, \envbuf, z])
// x.set(\gate, 0)
// z.plot
// Env([0, 1, 0], [0.5, 0.5], [8, -8]).plot