b = Buffer.read(s, "GeneratedTerrain2.wav".resolveRelative)


~mouseXA = {Lag.ar(K2A.ar(MouseX.kr))};
~mouseYA = {Lag.ar(K2A.ar(MouseY.kr))};

(
{
	[
		WaveTerrain.ar(b.bufnum, ~mouseXA.value, ~mouseYA.value, 4000, 4000),
		WaveTerrain.ar(b.bufnum, ~mouseXA.value * 0.99 + 0.1, ~mouseYA.value, 4000, 4000)
	]
}.play
)

{WaveTerrain.ar(b.bufnum, Lag.ar(K2A.ar([MouseX.kr, MouseX.kr * 0.99 + 1])) + SinOsc.ar(10, mul:0.04),
	Lag.ar(K2A.ar(MouseY.kr)) + SinOsc.ar(10, 0.5, mul:0.41), 4000,4000)}.play




{~mouseXA.value.poll}.play
WaveTerrain

Platform.userExtensionDir