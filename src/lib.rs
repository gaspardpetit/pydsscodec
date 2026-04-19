use dss_codec::demux;
use dss_codec::error::DecodeError;
use dss_codec::streaming::{
    DecryptStreamer as RustDecryptStreamer,
    DecryptingDecoderStreamer as RustDecryptingDecoderStreamer,
    StreamingDecoder as RustStreamingDecoder,
};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::path::Path;

#[pyclass(module = "pydsscodec._core")]
struct DecodedAudio {
    samples: Vec<f64>,
    sample_rate: u32,
    native_rate: u32,
    format: String,
}

#[pymethods]
impl DecodedAudio {
    #[getter]
    fn samples(&self) -> Vec<f64> {
        self.samples.clone()
    }

    #[getter]
    fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    #[getter]
    fn native_rate(&self) -> u32 {
        self.native_rate
    }

    #[getter]
    fn format(&self) -> &str {
        &self.format
    }

    #[getter]
    fn sample_count(&self) -> usize {
        self.samples.len()
    }

    #[getter]
    fn duration_seconds(&self) -> f64 {
        if self.sample_rate == 0 {
            0.0
        } else {
            self.samples.len() as f64 / self.sample_rate as f64
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "DecodedAudio(format={:?}, sample_rate={}, native_rate={}, sample_count={})",
            self.format,
            self.sample_rate,
            self.native_rate,
            self.samples.len()
        )
    }
}

#[pyclass(module = "pydsscodec._core")]
struct StreamingDecoder {
    inner: RustStreamingDecoder,
}

#[pymethods]
impl StreamingDecoder {
    #[new]
    fn new() -> Self {
        Self {
            inner: RustStreamingDecoder::new(),
        }
    }

    fn push(&mut self, data: &[u8]) -> PyResult<Vec<f64>> {
        self.inner.push(data).map_err(decode_error_to_pyerr)
    }

    fn finish(&mut self) -> PyResult<Vec<f64>> {
        self.inner.finish().map_err(decode_error_to_pyerr)
    }

    fn format(&self) -> Option<&'static str> {
        self.inner.format().map(format_name)
    }

    fn native_rate(&self) -> Option<u32> {
        self.inner.native_rate()
    }
}

#[pyclass(module = "pydsscodec._core")]
struct DecryptStreamer {
    inner: RustDecryptStreamer,
}

#[pymethods]
impl DecryptStreamer {
    #[new]
    #[pyo3(signature = (password=None))]
    fn new(password: Option<Vec<u8>>) -> Self {
        Self {
            inner: RustDecryptStreamer::new(password.as_deref()),
        }
    }

    fn push(&mut self, data: &[u8]) -> PyResult<Vec<u8>> {
        self.inner.push(data).map_err(decode_error_to_pyerr)
    }

    fn finish(&mut self) -> PyResult<Vec<u8>> {
        self.inner.finish().map_err(decode_error_to_pyerr)
    }
}

#[pyclass(module = "pydsscodec._core")]
struct DecryptingDecoderStreamer {
    inner: RustDecryptingDecoderStreamer,
}

#[pymethods]
impl DecryptingDecoderStreamer {
    #[new]
    #[pyo3(signature = (password=None))]
    fn new(password: Option<Vec<u8>>) -> Self {
        Self {
            inner: RustDecryptingDecoderStreamer::new(password.as_deref()),
        }
    }

    fn push(&mut self, data: &[u8]) -> PyResult<Vec<f64>> {
        self.inner.push(data).map_err(decode_error_to_pyerr)
    }

    fn finish(&mut self) -> PyResult<Vec<f64>> {
        self.inner.finish().map_err(decode_error_to_pyerr)
    }

    fn format(&self) -> Option<&'static str> {
        self.inner.format().map(format_name)
    }

    fn native_rate(&self) -> Option<u32> {
        self.inner.native_rate()
    }
}

#[pyfunction(signature = (data, password=None))]
fn decode_bytes(data: &[u8], password: Option<Vec<u8>>) -> PyResult<DecodedAudio> {
    let audio = dss_codec::decode_to_buffer_with_password(data, password.as_deref())
        .map_err(decode_error_to_pyerr)?;
    Ok(convert_audio(audio))
}

#[pyfunction(signature = (path, password=None))]
fn decode_file(path: &str, password: Option<Vec<u8>>) -> PyResult<DecodedAudio> {
    let audio = dss_codec::decode_file_with_password(Path::new(path), password.as_deref())
        .map_err(decode_error_to_pyerr)?;
    Ok(convert_audio(audio))
}

#[pyfunction(signature = (data, password=None))]
fn decrypt_bytes(data: &[u8], password: Option<Vec<u8>>) -> PyResult<Vec<u8>> {
    dss_codec::decrypt_to_bytes(data, password.as_deref()).map_err(decode_error_to_pyerr)
}

#[pyfunction(signature = (path, password=None))]
fn decrypt_file(path: &str, password: Option<Vec<u8>>) -> PyResult<Vec<u8>> {
    dss_codec::decrypt_file(Path::new(path), password.as_deref()).map_err(decode_error_to_pyerr)
}

#[pyfunction]
fn detect_format(data: &[u8]) -> Option<&'static str> {
    demux::detect_format(data).map(format_name)
}

#[pyfunction]
fn crate_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

fn convert_audio(audio: dss_codec::AudioBuffer) -> DecodedAudio {
    DecodedAudio {
        samples: audio.samples,
        sample_rate: audio.native_rate,
        native_rate: audio.native_rate,
        format: format_name(audio.format).to_string(),
    }
}

fn format_name(format: demux::AudioFormat) -> &'static str {
    match format {
        demux::AudioFormat::DssSp => "dss_sp",
        demux::AudioFormat::Ds2Sp => "ds2_sp",
        demux::AudioFormat::Ds2Qp => "ds2_qp",
    }
}

fn decode_error_to_pyerr(err: DecodeError) -> PyErr {
    PyRuntimeError::new_err(err.to_string())
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DecodedAudio>()?;
    m.add_class::<StreamingDecoder>()?;
    m.add_class::<DecryptStreamer>()?;
    m.add_class::<DecryptingDecoderStreamer>()?;
    m.add_function(wrap_pyfunction!(decode_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(decode_file, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt_file, m)?)?;
    m.add_function(wrap_pyfunction!(detect_format, m)?)?;
    m.add_function(wrap_pyfunction!(crate_version, m)?)?;
    Ok(())
}
