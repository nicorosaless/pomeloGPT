# Math Rendering Test Examples

Now you can use LaTeX math equations in your chat!

## Inline Math
Use single dollar signs for inline equations:
- The famous equation is $E = mc^2$
- A simple polynomial: $f(x) = x^2 + 2x + 1$
- Greek letters: $\\alpha, \\beta, \\gamma, \\Delta, \\Omega$

## Display Math
Use double dollar signs for centered display equations:

$$
\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$

$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

$$
\\nabla \\times \\vec{B} = \\mu_0 \\left(\\vec{J} + \\epsilon_0 \\frac{\\partial \\vec{E}}{\\partial t}\\right)
$$

## Matrix Example

$$
\\begin{bmatrix}
a & b \\\\
c & d
\\end{bmatrix}
\\begin{bmatrix}
x \\\\
y
\\end{bmatrix}
=
\\begin{bmatrix}
ax + by \\\\
cx + dy
\\end{bmatrix}
$$

## Common Deep Learning Equations

Softmax function:
$$
\\text{softmax}(z_i) = \\frac{e^{z_i}}{\\sum_{j=1}^{K} e^{z_j}}
$$

Cross-entropy loss:
$$
L = -\\sum_{i=1}^{n} y_i \\log(\\hat{y}_i)
$$

Gradient descent update:
$$
\\theta_{t+1} = \\theta_t - \\eta \\nabla L(\\theta_t)
$$
