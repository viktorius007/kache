//! The part of D-Bus the development-tier move needs: one `unix:path=`
//! connection, EXTERNAL authentication, method calls, and the header fields
//! of the messages that come back. Wire format: D-Bus Specification,
//! "Message Protocol" and "Authentication Protocol". Messages are written in
//! the host's byte order; a peer on the same host answers in it, and a
//! message in the other order is refused rather than decoded.

use std::io::{self, BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::time::Instant;

const ENDIAN: u8 = if cfg!(target_endian = "little") {
    b'l'
} else {
    b'B'
};
const METHOD_CALL: u8 = 1;
pub(super) const ERROR: u8 = 3;
const FIELD_PATH: u8 = 1;
const FIELD_INTERFACE: u8 = 2;
const FIELD_MEMBER: u8 = 3;
const FIELD_REPLY_SERIAL: u8 = 5;
const FIELD_DESTINATION: u8 = 6;
const FIELD_SIGNATURE: u8 = 8;
/// systemd's replies and signals are well under a page; anything this large
/// is not one of them.
const MAX_MESSAGE: usize = 1 << 20;

/// A marshalled value sequence. Alignment is relative to the start of the
/// buffer, which is correct for a body: a body starts on an 8-byte boundary.
#[derive(Default)]
pub(super) struct Writer(Vec<u8>);

impl Writer {
    pub(super) fn into_bytes(self) -> Vec<u8> {
        self.0
    }

    pub(super) fn align(&mut self, alignment: usize) -> &mut Self {
        let padded = self.0.len().next_multiple_of(alignment);
        self.0.resize(padded, 0);
        self
    }

    fn byte(&mut self, value: u8) -> &mut Self {
        self.0.push(value);
        self
    }

    pub(super) fn u32(&mut self, value: u32) -> &mut Self {
        self.align(4);
        self.0.extend_from_slice(&value.to_ne_bytes());
        self
    }

    /// `s` or `o`.
    pub(super) fn string(&mut self, value: &str) -> &mut Self {
        self.u32(value.len() as u32);
        self.0.extend_from_slice(value.as_bytes());
        self.byte(0)
    }

    /// `g`, also the signature inside a variant.
    pub(super) fn signature(&mut self, value: &str) -> &mut Self {
        self.byte(value.len() as u8);
        self.0.extend_from_slice(value.as_bytes());
        self.byte(0)
    }

    /// An array whose elements start on `element_alignment`. The length
    /// counts the elements only, not the padding before the first.
    pub(super) fn array(
        &mut self,
        element_alignment: usize,
        elements: impl FnOnce(&mut Self),
    ) -> &mut Self {
        self.u32(0);
        let length_at = self.0.len() - 4;
        self.align(element_alignment);
        let start = self.0.len();
        elements(self);
        let length = (self.0.len() - start) as u32;
        self.0[length_at..length_at + 4].copy_from_slice(&length.to_ne_bytes());
        self
    }

    fn header_field(&mut self, code: u8, signature: &str, value: &str) {
        self.align(8).byte(code).signature(signature);
        if signature == "g" {
            self.signature(value);
        } else {
            self.string(value);
        }
    }
}

/// One method call. `signature` is empty for a call without arguments.
pub(super) struct Call<'a> {
    pub(super) destination: &'a str,
    pub(super) path: &'a str,
    pub(super) interface: &'a str,
    pub(super) member: &'a str,
    pub(super) signature: &'a str,
    pub(super) body: &'a [u8],
}

impl Call<'_> {
    fn encode(&self, serial: u32) -> Vec<u8> {
        let mut message = Writer::default();
        message.byte(ENDIAN).byte(METHOD_CALL).byte(0).byte(1);
        message.u32(self.body.len() as u32).u32(serial);
        message.array(8, |fields| {
            fields.header_field(FIELD_PATH, "o", self.path);
            fields.header_field(FIELD_INTERFACE, "s", self.interface);
            fields.header_field(FIELD_MEMBER, "s", self.member);
            fields.header_field(FIELD_DESTINATION, "s", self.destination);
            if !self.signature.is_empty() {
                fields.header_field(FIELD_SIGNATURE, "g", self.signature);
            }
        });
        message.align(8).0.extend_from_slice(self.body);
        message.into_bytes()
    }
}

/// A received message: its type, the header fields a caller matches on,
/// and its body.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct Message {
    pub(super) kind: u8,
    pub(super) reply_serial: Option<u32>,
    pub(super) member: Option<String>,
    pub(super) body: Vec<u8>,
}

/// Reads values out of a marshalled buffer; `None` past its end.
pub(super) struct Reader<'a> {
    bytes: &'a [u8],
    at: usize,
}

impl<'a> Reader<'a> {
    pub(super) fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, at: 0 }
    }

    fn take(&mut self, length: usize) -> Option<&'a [u8]> {
        let taken = self.bytes.get(self.at..self.at.checked_add(length)?)?;
        self.at += length;
        Some(taken)
    }

    fn align(&mut self, alignment: usize) {
        self.at = self.at.next_multiple_of(alignment);
    }

    fn byte(&mut self) -> Option<u8> {
        Some(self.take(1)?[0])
    }

    pub(super) fn u32(&mut self) -> Option<u32> {
        self.align(4);
        Some(u32::from_ne_bytes(self.take(4)?.try_into().ok()?))
    }

    /// `s` or `o`, without its terminating NUL.
    pub(super) fn string(&mut self) -> Option<&'a str> {
        let length = self.u32()? as usize;
        let text = self.take(length)?;
        self.take(1)?;
        std::str::from_utf8(text).ok()
    }

    fn signature(&mut self) -> Option<&'a str> {
        let length = usize::from(self.byte()?);
        let text = self.take(length)?;
        self.take(1)?;
        std::str::from_utf8(text).ok()
    }
}

fn invalid(what: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, what.to_owned())
}

/// Decode one message from a reader positioned at its first byte.
pub(super) fn read_message(input: &mut impl Read) -> io::Result<Message> {
    let mut fixed = [0; 16];
    input.read_exact(&mut fixed)?;
    if fixed[0] != ENDIAN {
        return Err(invalid("D-Bus message in a foreign byte order"));
    }
    let word =
        |at: usize| u32::from_ne_bytes([fixed[at], fixed[at + 1], fixed[at + 2], fixed[at + 3]]);
    let (kind, body_length, fields_length) = (fixed[1], word(4), word(12));
    let fields_end = 16 + fields_length as usize;
    let total = fields_end.next_multiple_of(8) + body_length as usize;
    if total > MAX_MESSAGE {
        return Err(invalid("D-Bus message too large"));
    }
    let mut bytes = fixed.to_vec();
    bytes.resize(total, 0);
    input.read_exact(&mut bytes[16..])?;
    let mut message = Message {
        kind,
        reply_serial: None,
        member: None,
        body: bytes[fields_end.next_multiple_of(8)..].to_vec(),
    };
    let mut fields = Reader::new(&bytes[..fields_end]);
    fields.at = 16;
    while fields.at < fields_end {
        fields.align(8);
        read_header_field(&mut fields, &mut message).ok_or_else(|| invalid("D-Bus header"))?;
    }
    Ok(message)
}

fn read_header_field(fields: &mut Reader, message: &mut Message) -> Option<()> {
    let code = fields.byte()?;
    match fields.signature()? {
        "u" => {
            let value = fields.u32()?;
            if code == FIELD_REPLY_SERIAL {
                message.reply_serial = Some(value);
            }
        }
        "s" | "o" => {
            let value = fields.string()?;
            if code == FIELD_MEMBER {
                message.member = Some(value.to_owned());
            }
        }
        "g" => {
            fields.signature()?;
        }
        _ => return None,
    }
    Some(())
}

/// An authenticated connection to a message bus, every read and write
/// bounded by one deadline.
pub(super) struct Connection {
    stream: BufReader<UnixStream>,
    deadline: Instant,
    serial: u32,
}

impl Connection {
    /// Connect, authenticate as this process's user and say `Hello`.
    pub(super) fn open(socket: &Path, deadline: Instant) -> io::Result<Self> {
        let mut connection = Self {
            stream: BufReader::new(UnixStream::connect(socket)?),
            deadline,
            serial: 0,
        };
        // SAFETY: getuid has no preconditions and cannot fail.
        let uid = unsafe { libc::getuid() };
        connection.write(&auth_external(uid))?;
        connection.bound()?;
        let mut line = Vec::new();
        (&mut connection.stream)
            .take(256)
            .read_until(b'\n', &mut line)?;
        if !line.starts_with(b"OK ") {
            return Err(invalid("D-Bus authentication refused"));
        }
        connection.write(b"BEGIN\r\n")?;
        connection.call(&Call {
            destination: "org.freedesktop.DBus",
            path: "/org/freedesktop/DBus",
            interface: "org.freedesktop.DBus",
            member: "Hello",
            signature: "",
            body: &[],
        })?;
        Ok(connection)
    }

    /// Send a call without waiting for its reply.
    pub(super) fn call(&mut self, call: &Call) -> io::Result<()> {
        self.serial += 1;
        self.write(&call.encode(self.serial))
    }

    /// The next message from the bus.
    pub(super) fn next(&mut self) -> io::Result<Message> {
        self.bound()?;
        read_message(&mut self.stream)
    }

    fn write(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.bound()?;
        self.stream.get_ref().write_all(bytes)
    }

    fn bound(&self) -> io::Result<()> {
        let remaining = self
            .deadline
            .checked_duration_since(Instant::now())
            .filter(|remaining| !remaining.is_zero())
            .ok_or_else(|| io::Error::from(io::ErrorKind::TimedOut))?;
        let socket = self.stream.get_ref();
        socket.set_read_timeout(Some(remaining))?;
        socket.set_write_timeout(Some(remaining))
    }
}

/// The opening of the authentication conversation: a NUL byte, then
/// `AUTH EXTERNAL` with the decimal uid hex-encoded as ASCII.
fn auth_external(uid: u32) -> Vec<u8> {
    let hex: String = uid
        .to_string()
        .bytes()
        .map(|digit| format!("{digit:02x}"))
        .collect();
    format!("\0AUTH EXTERNAL {hex}\r\n").into_bytes()
}

#[cfg(test)]
#[path = "dbus_tests.rs"]
mod tests;
