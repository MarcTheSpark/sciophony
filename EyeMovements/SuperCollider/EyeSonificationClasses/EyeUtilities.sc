EyeUtilities {
	classvar outputLimiterFunction, outputLimiterGroup;
	*setOutputLimiter { |limit=1.0, globalMul=1.0, persevere=true, out=nil, numChannels=nil, server=nil|
		var limitOutput;
		// use default server by default, and limit all output channels by default
		server = server ? Server.default;
		out = out ? 0;
		numChannels = numChannels ? (server.options.numOutputBusChannels - out);
		// remove the old output limiter before placing a new one
		if(outputLimiterFunction.notNil, {MarcUtilities.removeOutputLimiter();});
		limitOutput = {
			SynthDef(\outputLimiter, {
				// write to the bus, replacing previous contents
				ReplaceOut.ar(out, Limiter.ar(In.ar(out, numChannels), limit) * globalMul);
			}).send(server);
			{
				server.sync;
				outputLimiterGroup = Group.tail(RootNode(server));
				Synth(\outputLimiter, target:outputLimiterGroup, addAction:\addToTail);
			}.fork;
		};
		if(persevere, {
			CmdPeriod.add(limitOutput);
		});
		outputLimiterFunction = limitOutput;
		limitOutput.value;
	}

	*removeOutputLimiter {
		CmdPeriod.remove(outputLimiterFunction);
		outputLimiterGroup.free;
		outputLimiterFunction = nil;
		outputLimiterGroup = nil;
	}
}
