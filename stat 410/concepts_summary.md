# STAT 410 Course Concepts Summary

**Last Updated:** February 4, 2026

## Week 1: Transformations of One Random Variable (Sections 1.7-1.8)

### New Concepts (not STAT 400 review)

1. **CDF Technique for Transformations**
   - Given Y = g(X), find F_Y(y) = P(g(X) ≤ y)
   - Work through the inequality to express in terms of X
   - Differentiate to get f_Y(y)

2. **Change-of-Variable Theorem (Theorem 1.7.1)**
   - For one-to-one, differentiable g(x):
   - f_Y(y) = f_X(g⁻¹(y)) · |dx/dy|
   - Key: multiply by absolute value of Jacobian

3. **MGF Approach**
   - M_Y(t) = E(e^{g(X)t}) to identify distribution
   - Useful when transformation matches known MGF form

---

## Week 2: Special Transformations + Probability Integral Transform

### New Concepts

1. **Chi-square from Normal**
   - If Z ~ N(0,1), then X = Z² ~ χ²(1)
   - Derived using change-of-variable with two branches

2. **Probability Integral Transform (Fact 1)**
   - If U ~ Uniform(0,1) and X = F⁻¹(U), then X has CDF F
   - Used for random variable simulation

3. **Inverse Transform (Fact 2)**
   - If X has CDF F (strictly increasing), then U = F(X) ~ Uniform(0,1)
   - Foundation for goodness-of-fit tests

4. **Mixed Random Variables**
   - Variables with both discrete atoms and continuous density
   - CDF has jumps at discrete points, continuous elsewhere

---

## Week 3: Joint Distributions + Conditional Expectations (Sections 2.1-2.3)

### New Concepts

1. **Joint PDF/PMF**
   - f(x,y) for continuous, p(x,y) for discrete
   - Must integrate/sum to 1 over support
   - Support often non-rectangular (depends on both x and y)

2. **Marginal Distributions**
   - f_X(x) = ∫ f(x,y) dy (integrate out y)
   - f_Y(y) = ∫ f(x,y) dx (integrate out x)
   - **Critical**: bounds may depend on the other variable
   - Often requires splitting into cases (e.g., 0 < y ≤ 2 vs 2 < y < 4)

3. **Conditional Distribution**
   - f_{X|Y}(x|y) = f(x,y) / f_Y(y)
   - "Slice" the joint distribution at fixed y, renormalize

4. **Conditional Expectation**
   - E(X|Y=y) = ∫ x · f_{X|Y}(x|y) dx
   - E(X|Y) is a random variable (function of Y)

5. **Law of Iterated Expectation**
   - E(E(X|Y)) = E(X)
   - "Average of conditional averages = unconditional average"

6. **Properties of Conditional Expectation**
   - E(a₁X₁ + a₂X₂ | Y) = a₁E(X₁|Y) + a₂E(X₂|Y) (linearity)
   - E(g(Y) | Y) = g(Y) (known function pulls out)
   - E(g(Y)X | Y) = g(Y)E(X|Y)

7. **Independence Test**
   - X, Y independent iff:
     - Support is rectangular (product of intervals), AND
     - f(x,y) = f_X(x) · f_Y(y) for all (x,y)
   - Non-rectangular support → automatically dependent

---

## Homework Topics

| HW | Sections | Key Skills |
|----|----------|------------|
| HW01 | 1.7-1.8 | CDF technique, change-of-variable, transformations of single r.v. |
| HW02 | 2.1-2.3 | Joint pdf, marginals (with case-splitting), probabilities via double integrals, independence |

---

## Common Pitfalls

1. **Marginal of Y**: bounds on x often depend on y → must split into cases
2. **Decreasing transformations**: F_W(w) = 1 - F_X(...) when W decreases as X increases
3. **Independence**: non-rectangular support = NOT independent (no calculation needed)
4. **Probability regions**: always sketch the constraint (line/curve) against support first
