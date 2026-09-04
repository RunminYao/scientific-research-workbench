# Finite-amplitude pendulum derivation

For a point mass, rigid massless rod, no damping, and uniform gravitational acceleration, energy conservation gives the exact period

\[
T = 4\sqrt{L/g}\,K(k),\qquad k=\sin(\theta_0/2).
\]

Using \(K(k)=\frac{\pi}{2}[1+\frac14k^2+\frac{9}{64}k^4+O(k^6)]\) and expanding \(k\) in the peak angle gives

\[
\frac{T}{T_0}=1+\frac{\theta_0^2}{16}+\frac{11\theta_0^4}{3072}+O(\theta_0^6),\qquad T_0=2\pi\sqrt{L/g}.
\]

The truncation is an asymptotic small-angle statement. This example verifies it only at \(\theta_0=0.2\) rad and does not claim accuracy near the separatrix \(\theta_0=\pi\).
