// could have them get louder over time? To compensate for lower density?

1000::ms => dur cDur;
9 => float startDelayRatio;
0.1 => float rate;   // minimum playback speed
3. / 2. => float rateRatio;

load( me.dir() + "frogblock.wav" ) @=> LiSa2 @ lisa;

lisa.maxVoices( 30 );
// set voice pan
for( int v; v < lisa.maxVoices(); v++ )
{
    // can pan across all available channels
    // note LiSa.pan( voice, [0...channels-1] )
    lisa.pan( v, Math.random2f( 0, lisa.channels()-1 ) );
}

lisa => GVerb gverb => dac;
lisa => dac;
50 => gverb.roomsize;
3::second => gverb.revtime;
0 => gverb.dry;
0.2 => gverb.early;
0.5 => gverb.tail;
0.1 => gverb.gain;

// create a new LiSa pre-loaded with the specified file
fun LiSa2 load( string filename )
{
    // sound buffer
    SndBuf buffy;
    // load it
    filename => buffy.read;
    
    // instantiate new LiSa (will be returned)
    LiSa2 lisa;
    // set duration
    buffy.samples()::samp => lisa.duration;
    
    // transfer values from SndBuf to LiSa
    for( 0 => int i; i < buffy.samples(); i++ )
    {
        // args are sample value and sample index
        // (dur must be integral in samples)
        lisa.valueAt( buffy.valueAt(i), i::samp );        
    }
    
    // set default LiSa parameters; actual usage parameters intended
    // to be set to taste by the user after this function returns
    lisa.play( false );
    lisa.loop( false );
    
    return lisa;
}

fun void playgrain(dur length, float rate) {
    lisa.getVoice() => int newvoice;
    lisa.playPos(newvoice, 0::ms);
    lisa.play(newvoice, 1);
    lisa.rate(newvoice, rate);
    lisa.rampDown(newvoice, length);
    lisa.loop(newvoice, 0);
    length => now;
}

fun void extendDurArray(dur arraySoFar[], dur newDur) {
    // Loop through the second array and add each element to the first array
    arraySoFar.size() => int currentSize;
    arraySoFar << newDur;
    for (0 => int i; i < currentSize; i++) {
        arraySoFar << arraySoFar[i];
    }
}

fun printArray(dur array[]) {
    for (dur myDur: array) {
        chout <= myDur / 1::ms <= ", ";
    }
    chout <= IO.newline();
}

fun cantor(dur minDur, float rate) {
    [minDur] @=> dur patternSoFar[];
    minDur @=> dur longestRest;
    playgrain(minDur, rate);
    minDur => now;
    while (true) {
        longestRest * 3 => longestRest;
        playgrain(minDur, rate);
        longestRest => now;
        for (dur rest: patternSoFar) {
            playgrain(minDur, rate);
            rest => now;
        }
        
        extendDurArray(patternSoFar, longestRest);
    }
}

cDur * startDelayRatio => dur startDelay;
while (cDur > 3::samp) { 
    spork ~ cantor(cDur, rate);
    startDelay => now;
    cDur / 2 => cDur;
    <<<rateRatio>>>;
    rate * rateRatio => rate;
}

while( true ) {
    1::second => now;
}