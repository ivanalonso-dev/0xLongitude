"""
0xLongitude - Regresión logística L2 y métricas solo con numpy.

Sustituye a scikit-learn (en el equipo de Ivan, Windows bloquea sus DLL compiladas).
Misma función objetivo que sklearn.linear_model.LogisticRegression con penalización L2:
    0.5 * ||W||^2  +  C * sum_i  pérdida_logística_i      (el intercepto no se penaliza)
Se resuelve con Newton-Raphson y búsqueda de paso, así que llega al mismo óptimo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _softmax(Z: np.ndarray) -> np.ndarray:
    Z = Z - Z.max(axis=1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(axis=1, keepdims=True)


class LogisticRegression:
    """Interfaz mínima compatible: LogisticRegression(C=..., max_iter=...).fit(X, y).predict_proba(X)."""

    def __init__(self, C: float = 1.0, max_iter: int = 100, tol: float = 1e-10, **_ignorado):
        self.C, self.max_iter, self.tol = float(C), int(max_iter), tol

    # ---------------- binaria ----------------
    def _fit_binaria(self, X, y):
        n, d = X.shape
        Xb = np.column_stack([X, np.ones(n)])
        w = np.zeros(d + 1)
        reg = np.r_[np.ones(d), 0.0]

        def objetivo(w):
            z = Xb @ w
            return 0.5 * np.sum(reg * w * w) + self.C * np.sum(np.logaddexp(0, z) - y * z)

        f = objetivo(w)
        for _ in range(min(self.max_iter, 200)):
            p = 1 / (1 + np.exp(-(Xb @ w)))
            g = reg * w + self.C * Xb.T @ (p - y)
            s = p * (1 - p)
            H = np.diag(reg) + self.C * (Xb.T * s) @ Xb + 1e-12 * np.eye(d + 1)
            paso = np.linalg.solve(H, g)
            t = 1.0
            while t > 1e-8:
                w_n = w - t * paso
                f_n = objetivo(w_n)
                if f_n <= f - 1e-4 * t * g @ paso:
                    break
                t *= 0.5
            w, f_prev, f = w_n, f, f_n
            if abs(f_prev - f) < self.tol * max(1.0, abs(f)):
                break
        self.coef_ = w[:d][None, :]
        self.intercept_ = w[d:]

    # ---------------- multinomial ----------------
    def _fit_multinomial(self, X, Y):
        n, d = X.shape
        K = Y.shape[1]
        Xb = np.column_stack([X, np.ones(n)])
        D = d + 1
        W = np.zeros((K, D))
        reg = np.tile(np.r_[np.ones(d), 0.0], K)

        def objetivo(W):
            Z = Xb @ W.T
            lse = np.logaddexp.reduce(Z, axis=1)
            return 0.5 * np.sum(reg * W.ravel() ** 2) + self.C * np.sum(lse - np.sum(Y * Z, axis=1))

        f = objetivo(W)
        for _ in range(min(self.max_iter, 200)):
            P = _softmax(Xb @ W.T)
            g = reg * W.ravel() + self.C * ((P - Y).T @ Xb).ravel()
            # Hessiano: sum_i (diag(p_i) - p_i p_i^T) (x) x_i x_i^T
            A = np.einsum("ik,kl->ikl", P, np.eye(K)) - np.einsum("ik,il->ikl", P, P)
            H = self.C * np.einsum("ikl,ia,ib->kalb", A, Xb, Xb).reshape(K * D, K * D)
            H += np.diag(reg) + 1e-8 * np.eye(K * D)      # 1e-8: invariancia del softmax en los interceptos
            paso = np.linalg.solve(H, g).reshape(K, D)
            t = 1.0
            while t > 1e-8:
                W_n = W - t * paso
                f_n = objetivo(W_n)
                if f_n <= f - 1e-4 * t * g @ paso.ravel():
                    break
                t *= 0.5
            W, f_prev, f = W_n, f, f_n
            if abs(f_prev - f) < self.tol * max(1.0, abs(f)):
                break
        self.coef_ = W[:, :d]
        self.intercept_ = W[:, d]

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y)
        self.classes_ = np.unique(y)
        if len(self.classes_) == 2:
            self._fit_binaria(X, (y == self.classes_[1]).astype(float))
        else:
            Y = (y[:, None] == self.classes_[None, :]).astype(float)
            self._fit_multinomial(X, Y)
        return self

    def predict_proba(self, X):
        X = np.asarray(X, float)
        if len(self.classes_) == 2:
            p = 1 / (1 + np.exp(-(X @ self.coef_[0] + self.intercept_[0])))
            return np.column_stack([1 - p, p])
        return _softmax(X @ self.coef_.T + self.intercept_)


# ---------------- métricas ----------------
def log_loss(y, p, labels=None) -> float:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier_score_loss(y, p) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean((p - y) ** 2))


def roc_auc_score(y, p) -> float:
    y, p = np.asarray(y), np.asarray(p, float)
    n1, n0 = (y == 1).sum(), (y == 0).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    rangos = pd.Series(p).rank(method="average").to_numpy()
    return float((rangos[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
