# Matrix-vector multiplication

For matrix `G` and vector `V`, output element `j` is:

```text
I[j] = sum(G[j, i] × V[i])
```

A crossbar maps vector elements to row voltages, matrix elements to cell conductances, and output elements to summed column currents under the orientation used in this repository.
