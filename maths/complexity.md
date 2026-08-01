# Complexity and physical parallelism

Calling crossbar MVM `O(1)` describes an idealized operation only when the entire matrix is physically resident and all rows and columns operate concurrently. A real layer may require many finite tiles, bit slices, ADC conversions, communication steps, and digital accumulations.

Always distinguish:

1. arithmetic operation count;
2. latency of one resident physical array;
3. latency and energy of the complete accelerator.
