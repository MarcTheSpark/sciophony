(
~hmap = HeightMap(200, 200, [
	[0.5, 0.9, 7, 6],
	[0.1, 0.1, 5, 3]
]);
)

(
{
	var height = ~hmap.interp(MouseX.kr, MouseY.kr);
	height.poll;
	SinOsc.ar(440 + height.linlin(0, 7, 0, 500), mul:0.1) ! 2;
}.play
)