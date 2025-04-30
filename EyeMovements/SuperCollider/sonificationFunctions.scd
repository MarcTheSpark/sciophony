/**
Defines a bunch of sonification functions as global variables
**/

(
    ~harpStrum = {
        |scale=(Scale.minorPentatonic), scaleRootFreq=110, numStrings=25, pitchHeight="~y", trigRate="~s.linlin(0, 2, 6, 28)", amp="~s.linexp(0, 2, 0.02, 0.2)", pan="~x"|

        { |positionStream| { |gate=1|
            var paramInterpreter = positionStream.getParamInterpreter;
            var pitchHeightInterpreted = paramInterpreter.(pitchHeight);
            var trigRateInterpreted = paramInterpreter.(trigRate);
            var ampInterpreted = paramInterpreter.(amp);
            var panInterpreted = paramInterpreter.(pan);
            var mainTrig = Impulse.kr(trigRateInterpreted);
            var trigIndex = pitchHeightInterpreted.linlin(0, 1, 0, numStrings).floor;

            var plucks = Array.fill(numStrings, { |i|
                var freq = scale.degreeToFreq(i, scaleRootFreq , 0);
                var env = Env.new([0,1, 1, 0],[0.001,0.006, 0.0005],[5,-5, -8]);
                var inp = ampInterpreted * LFClipNoise.ar(2000) * EnvGen.ar(env, mainTrig * BinaryOpUGen('==', trigIndex, i));
                // the LFNoise here creates a fun detuning effect. Try increasing it.
                var plucker = DWGPluckedStiff.ar(freq * LFNoise2.kr(0.1).linexp(-1, 1, 0.99, 1.01), ampInterpreted, c1:4, c3:20, inp:inp, release:1, fB:80);
                Pan2.ar(
                    plucker,
                    panInterpreted
                );
            });
            Out.ar(~mixBus, Mix.ar(plucks) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };


    ~mapGranulator = {
        |sourceMap, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)"|

        { |positionStream| { |gate=1|
            var paramInterpreter = positionStream.getParamInterpreter;
            var pos = paramInterpreter.("[~x, ~y]");
            var trigRateInterpreted = paramInterpreter.(trigRate);
            var ampInterpreted = paramInterpreter.(amp);
            var durInterpreted = paramInterpreter.(dur);
            var panInterpreted = paramInterpreter.(pan);

            // Calculate distances to each source location
            var distances = sourceMap.collect { |src|
                var locX = src[\location][0];
                var locY = src[\location][1];
                hypot(pos[0] - locX, pos[1] - locY); // Euclidean distance
            };

            // Invert distances to create probabilities (closer distance -> higher probability)
            var invDistances = distances.collect { |dist| 1 / (dist + 0.001) }; // Small offset to avoid division by zero

            // Normalize the inverted distances to sum to 1
            var total = invDistances.sum;
            var volumes = (invDistances / total).pow(1.5) * 2;

            // Main trigger
            var mainTrig = Impulse.kr(trigRateInterpreted);

            // Create grains for each buffer, modulating their amplitudes based on distance
            var grains = Mix(sourceMap.collect { |src, i|
                GrainBuf.ar(
                    2,
                    mainTrig,
                    durInterpreted,
                    src[\buf].bufnum,
                    pos[0].linexp(0, 1, 1.1, 1.6),
                    WhiteNoise.kr.linlin(-1, 1, src[\sourceRange][0], src[\sourceRange][1]),
                    2,
                    panInterpreted
                ) * volumes[i] * ampInterpreted;
            });

            // Output the mixed grains, scaled by amp
            Out.ar(~mixBus, grains * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };

    ~simpleSines = {
        |freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)"|
        { |positionStream| { |gate=1|
            var paramInterpreter = positionStream.getParamInterpreter;

            freq = paramInterpreter.(freq);
            vol = paramInterpreter.(vol);
            pan = paramInterpreter.(pan);
            Out.ar(~mixBus, Pan2.ar(SinOsc.ar(freq, mul:vol), pan) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };

    ~whistle = {
        |freq="(~x + ~y).linexp(0, 2, 300, 1500)", vol="~s.linexp(0, 2, 0.01, 0.3)", pan="~x.linlin(0, 1, -1, 1)", rq="0.005"|
        { |positionStream| { |gate=1|
            var whistle;
            var paramInterpreter = positionStream.getParamInterpreter;
            freq = paramInterpreter.(freq);
            vol = paramInterpreter.(vol);
            pan = paramInterpreter.(pan);
            rq = paramInterpreter.(rq);
            whistle = BPF.ar(PinkNoise.ar, freq, rq, mul:vol/rq);
            Out.ar(~mixBus, Pan2.ar(whistle, pan) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };


    ~saccadeTrigger = {
        |soundBuf, rate="~s.linexp(0, 4, 0.5, 1.5)", amp="~s.linexp(0, 4, 0.2, 0.5)", pan="~x.linlin(0, 1, -1, 1)", startTime=0|
        { |positionStream| { |gate=1|
            var paramInterpreter = positionStream.getParamInterpreter;
            rate = paramInterpreter.(rate);
            amp = paramInterpreter.(amp);
            pan = paramInterpreter.(pan);
            Out.ar(~mixBus, Pan2.ar(
                PlayBuf.ar(soundBuf.numChannels, soundBuf, rate:rate, trigger: positionStream.detectSaccades, startPos: startTime * SampleRate.ir) * amp * EnvGate(gate:gate, fadeTime:0.15),
                pan
            ));
        } };
    };


    ~simpleGranulator = {
        |soundBuf, trigRate="~s.linlin(0, 2, 30, 80)", amp="~s.linexp(0, 2, 0.2, 1.0)", dur="0.05", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.5, 0.5)", synchronous=true|

        { |positionStream| { |gate=1|
            var grains;
            var paramInterpreter = positionStream.getParamInterpreter;
            trigRate = paramInterpreter.(trigRate);
            amp = paramInterpreter.(amp);
            dur = paramInterpreter.(dur);
            pan = paramInterpreter.(pan);
            playRate = paramInterpreter.(playRate);
            playPos = paramInterpreter.(playPos);

            // Create grains for each buffer, modulating their amplitudes based on distance
            grains = GrainBuf.ar(
                2,
                synchronous.if({Impulse.kr(trigRate)}, {Dust.kr(trigRate)}),
                dur,
                soundBuf,
                playRate,
                playPos,
                2,
                pan
            );

            // Output the mixed grains, scaled by amp
            Out.ar(~mixBus, grains * amp * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };

    ~velTrigger = {
        |soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="800"|
        { |positionStream| { |gate=1|
            var player, env;
            var trig = (positionStream.speed.lag(0.2) > speedThresh);
            var paramInterpreter = positionStream.getParamInterpreter;
            envelope = paramInterpreter.(envelope);
            amp = paramInterpreter.(amp);
            pan = paramInterpreter.(pan);
            playRate = paramInterpreter.(playRate);
            playPos = paramInterpreter.(playPos);
            bpfFreq = paramInterpreter.(bpfFreq);
            player = PlayBuf.ar(1, soundBuf, trigger: trig, startPos: WhiteNoise.kr(0.4, 0.5) * BufFrames.ir(soundBuf));
            env = EnvGen.kr(envelope, trig, amp);
            Out.ar(~mixBus, Pan2.ar(BPF.ar(player * env, bpfFreq), pan) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };

    ~velTriggerChoice = {
        |soundBufs, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="800"|
        { |positionStream| { |gate=1|
            var player, env, bufIdx;
            var trig = (positionStream.speed.lag(0.2) > speedThresh);
            var paramInterpreter = positionStream.getParamInterpreter;
            envelope = paramInterpreter.(envelope);
            amp = paramInterpreter.(amp);
            pan = paramInterpreter.(pan);
            playRate = paramInterpreter.(playRate);
            playPos = paramInterpreter.(playPos);
            bpfFreq = paramInterpreter.(bpfFreq);

            bufIdx = TIRand.kr(0, soundBufs.size - 1, trig);

            player = PlayBuf.ar(1, Select.kr(bufIdx, soundBufs), trigger: trig);
            env = EnvGen.kr(envelope, trig, amp);
            Out.ar(~mixBus, Pan2.ar(BPF.ar(player * env, bpfFreq), pan) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };

    ~velTriggerRingMod = {
        |soundBuf, envelope="Env.perc(0.05, 0.7)", speedThresh=5, amp="~s.linexp(0, 2, 0.2, 1.0)", pan="~x.linlin(0, 1, -1, 1)", playRate="1", playPos="WhiteNoise.kr(0.4, 0.5)", rq=0.1, bpfFreq="~y.linexp(0, 1, 3000, 400)", ringFreq="~y.linexp(0, 1, 3000, 400)"|
        { |positionStream| { |gate=1|
            var player, env;
            var trig = (positionStream.speed.lag(0.2) > speedThresh);
            var paramInterpreter = positionStream.getParamInterpreter;
            envelope = paramInterpreter.(envelope);
            amp = paramInterpreter.(amp);
            pan = paramInterpreter.(pan);
            playRate = paramInterpreter.(playRate);
            playPos = paramInterpreter.(playPos);
            bpfFreq = paramInterpreter.(bpfFreq);
            ringFreq = paramInterpreter.(ringFreq);
            player = PlayBuf.ar(1, soundBuf, trigger: trig, startPos: WhiteNoise.kr(0.4, 0.5) * BufFrames.ir(soundBuf));
            env = EnvGen.kr(envelope, trig, amp);
            Out.ar(~mixBus, Pan2.ar(BPF.ar(player * env, bpfFreq) * SinOsc.ar(bpfFreq), pan) * EnvGate(gate:gate, fadeTime:0.15));
        } };
    };
)