//! Error type for model loading and inference.
//!
//! Vendored from bosk (see `mod.rs`); trimmed to the pure-Rust LightGBM path: no file I/O, no
//! other backends.

use std::fmt;

/// Convenience alias for results returned by this module.
pub type Result<T> = std::result::Result<T, Error>;

/// Everything that can go wrong loading or evaluating a model.
#[derive(Debug)]
#[non_exhaustive]
pub enum Error {
    /// The model text could not be parsed. `line` is 1-based.
    Parse {
        /// 1-based line number the failure was found on.
        line: usize,
        /// Human-readable description of what could not be parsed.
        message: String,
    },

    /// The text parsed but contained no decision trees.
    EmptyModel,

    /// The model uses a capability this module does not implement (e.g. linear trees). Refusing
    /// to load is deliberate: evaluating such a model with the supported subset would return
    /// silently wrong predictions.
    Unsupported {
        /// What the model needs that is not implemented.
        message: String,
    },

    /// A dense feature vector has the wrong length for the model. Refusing to predict is
    /// deliberate: the model would silently treat the out-of-range features as missing.
    FeatureCount {
        /// The number of features the model was trained on.
        expected: usize,
        /// The number of features that was passed in.
        got: usize,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Parse { line, message } => write!(f, "parse error on line {line}: {message}"),
            Error::EmptyModel => write!(f, "no decision trees found in model"),
            Error::Unsupported { message } => write!(f, "unsupported model: {message}"),
            Error::FeatureCount { expected, got } => {
                write!(f, "model expects {expected} features, got {got}")
            }
        }
    }
}

impl std::error::Error for Error {}
