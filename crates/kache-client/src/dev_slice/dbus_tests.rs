//! Expected bytes are derived by hand from the D-Bus Specification's
//! marshalling rules, not produced by the writer under test.

use super::*;
use std::io::Cursor;
use std::os::unix::net::UnixListener;
use std::time::Duration;

fn call(body: &[u8]) -> Call<'_> {
    Call {
        destination: "d",
        path: "/p",
        interface: "i",
        member: "m",
        signature: "s",
        body,
    }
}

#[cfg(target_endian = "little")]
#[test]
fn a_method_call_marshals_its_header_fields_on_8_byte_boundaries() {
    let mut expected: Vec<u8> = Vec::new();
    expected.extend(b"l\x01\x00\x01"); // little-endian method call, protocol 1
    expected.extend(b"\x06\0\0\0"); // body length
    expected.extend(b"\x03\0\0\0"); // serial
    expected.extend(b"\x47\0\0\0"); // 12..16 fields length 71
    expected.extend(b"\x01\x01o\0\x02\0\0\0/p\0"); // 16..27 path
    expected.extend(b"\0\0\0\0\0"); // pad to 32
    expected.extend(b"\x02\x01s\0\x01\0\0\0i\0"); // 32..42 interface
    expected.extend(b"\0\0\0\0\0\0"); // pad to 48
    expected.extend(b"\x03\x01s\0\x01\0\0\0m\0"); // 48..58 member
    expected.extend(b"\0\0\0\0\0\0"); // pad to 64
    expected.extend(b"\x06\x01s\0\x01\0\0\0d\0"); // 64..74 destination
    expected.extend(b"\0\0\0\0\0\0"); // pad to 80
    expected.extend(b"\x08\x01g\0\x01s\0"); // 80..87 signature
    expected.extend(b"\0"); // pad to 88, the body
    expected.extend(b"\x01\0\0\0x\0");
    assert_eq!(call(b"\x01\0\0\0x\0").encode(3), expected);
}

#[test]
fn a_call_without_arguments_has_no_signature_field() {
    let message = Call {
        signature: "",
        ..call(&[])
    }
    .encode(1);
    let fields_length = u32::from_ne_bytes(message[12..16].try_into().unwrap());
    // path, interface, member and destination end at 74; no signature at 80.
    assert_eq!(fields_length, 74 - 16);
    assert_eq!(message.len(), 80);
}

#[test]
fn a_decoded_call_keeps_its_member_and_body() {
    let message = read_message(&mut Cursor::new(call(b"\x01\0\0\0x\0").encode(3))).unwrap();
    assert_eq!(
        message,
        Message {
            kind: METHOD_CALL,
            reply_serial: None,
            member: Some("m".into()),
            body: b"\x01\0\0\0x\0".to_vec(),
        }
    );
}

#[cfg(target_endian = "little")]
fn error_reply() -> Vec<u8> {
    let mut message: Vec<u8> = Vec::new();
    message.extend(b"l\x03\x01\x01"); // error
    message.extend(b"\x00\0\0\0"); // no body
    message.extend(b"\x09\0\0\0"); // serial
    message.extend(b"\x08\0\0\0"); // fields length
    message.extend(b"\x05\x01u\0\x03\0\0\0"); // 16..24 reply serial 3
    message
}

#[cfg(target_endian = "little")]
#[test]
fn an_error_reply_names_the_call_it_answers() {
    assert_eq!(
        read_message(&mut Cursor::new(error_reply())).unwrap(),
        Message {
            kind: ERROR,
            reply_serial: Some(3),
            member: None,
            body: Vec::new(),
        }
    );
}

#[cfg(target_endian = "little")]
#[test]
fn a_message_in_the_other_byte_order_is_refused() {
    let mut message = error_reply();
    message[0] = b'B';
    let error = read_message(&mut Cursor::new(message)).unwrap_err();
    assert!(error.to_string().contains("byte order"), "{error}");
}

#[cfg(target_endian = "little")]
#[test]
fn a_header_field_of_an_unknown_type_is_refused() {
    let mut message = error_reply();
    message[18] = b'y';
    let error = read_message(&mut Cursor::new(message)).unwrap_err();
    assert!(error.to_string().contains("D-Bus header"), "{error}");
}

#[cfg(target_endian = "little")]
#[test]
fn a_truncated_header_field_is_refused() {
    let mut message = error_reply();
    message[12] = 4; // the reply serial's value lies past the fields
    message.truncate(24);
    assert!(read_message(&mut Cursor::new(message)).is_err());
}

#[cfg(target_endian = "little")]
fn with_body_length(length: u32) -> Vec<u8> {
    let mut message = error_reply();
    message[4..8].copy_from_slice(&length.to_le_bytes());
    message.resize(24 + length as usize, 0);
    message
}

#[cfg(target_endian = "little")]
#[test]
fn a_message_of_exactly_one_mebibyte_is_read() {
    let message = read_message(&mut Cursor::new(with_body_length((1 << 20) - 24))).unwrap();
    assert_eq!(message.body.len(), (1 << 20) - 24);
}

#[cfg(target_endian = "little")]
#[test]
fn a_message_over_one_mebibyte_is_refused_before_it_is_read() {
    let error = read_message(&mut Cursor::new(with_body_length((1 << 20) - 23))).unwrap_err();
    assert!(error.to_string().contains("too large"), "{error}");
}

#[test]
fn signature_fields_are_skipped_whole() {
    let mut header = Writer::default();
    header.header_field(FIELD_SIGNATURE, "g", "uoss");
    header.header_field(FIELD_MEMBER, "s", "JobRemoved");
    let bytes = header.into_bytes();
    let mut fields = Reader::new(&bytes);
    let mut message = Message {
        kind: 4,
        reply_serial: None,
        member: None,
        body: Vec::new(),
    };
    read_header_field(&mut fields, &mut message).unwrap();
    fields.align(8);
    read_header_field(&mut fields, &mut message).unwrap();
    assert_eq!(message.member.as_deref(), Some("JobRemoved"));
}

#[test]
fn external_authentication_sends_the_decimal_uid_hex_encoded() {
    assert_eq!(auth_external(1002), b"\0AUTH EXTERNAL 31303032\r\n");
}

fn read_line(stream: &mut UnixStream) -> Vec<u8> {
    let mut line = Vec::new();
    let mut byte = [0];
    while line.last() != Some(&b'\n') && stream.read_exact(&mut byte).is_ok() {
        line.push(byte[0]);
    }
    line
}

/// A bus that answers authentication with `reply` and records what the
/// client sent until it hangs up.
fn fake_bus(reply: &'static [u8]) -> (tempfile::TempDir, std::thread::JoinHandle<Vec<u8>>) {
    let root = tempfile::tempdir().unwrap();
    let listener = UnixListener::bind(root.path().join("bus")).unwrap();
    let server = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        let mut received = read_line(&mut stream);
        let _ = stream.write_all(reply);
        let _ = stream.read_to_end(&mut received);
        received
    });
    (root, server)
}

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(30)
}

#[test]
fn an_accepted_client_begins_and_says_hello_as_serial_1() {
    let (root, server) = fake_bus(b"OK 0123456789abcdef\r\n");
    let connection = Connection::open(&root.path().join("bus"), deadline()).unwrap();
    drop(connection);
    let received = server.join().unwrap();
    let uid = unsafe { libc::getuid() };
    let mut expected = auth_external(uid);
    expected.extend(b"BEGIN\r\n");
    assert!(received.starts_with(&expected), "{received:?}");
    let hello = &received[expected.len()..];
    assert_eq!(u32::from_ne_bytes(hello[8..12].try_into().unwrap()), 1);
    let message = read_message(&mut Cursor::new(hello)).unwrap();
    assert_eq!(message.member.as_deref(), Some("Hello"));
}

#[test]
fn a_rejected_client_does_not_connect() {
    let (root, server) = fake_bus(b"REJECTED EXTERNAL\r\n");
    let error = Connection::open(&root.path().join("bus"), deadline())
        .err()
        .unwrap();
    assert!(error.to_string().contains("refused"), "{error}");
    let received = server.join().unwrap();
    let uid = unsafe { libc::getuid() };
    assert_eq!(received, auth_external(uid), "nothing follows a refusal");
}

#[test]
fn a_passed_deadline_ends_the_conversation_before_it_starts() {
    let (root, server) = fake_bus(b"OK 0123456789abcdef\r\n");
    let socket = root.path().join("bus");
    let error = Connection::open(&socket, Instant::now()).err().unwrap();
    assert_eq!(error.kind(), io::ErrorKind::TimedOut);
    assert_eq!(server.join().unwrap(), b"", "nothing was sent");
}

#[cfg(target_endian = "little")]
#[test]
fn each_call_takes_the_next_serial_and_replies_are_read_back() {
    let root = tempfile::tempdir().unwrap();
    let listener = UnixListener::bind(root.path().join("bus")).unwrap();
    let server = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        read_line(&mut stream);
        stream.write_all(b"OK 0123456789abcdef\r\n").unwrap();
        stream.write_all(&error_reply()).unwrap();
        let mut received = Vec::new();
        let _ = stream.read_to_end(&mut received);
        received
    });
    let mut connection = Connection::open(&root.path().join("bus"), deadline()).unwrap();
    connection.call(&call(b"\x01\0\0\0x\0")).unwrap();
    assert_eq!(connection.next().unwrap().reply_serial, Some(3));
    drop(connection);
    let received = server.join().unwrap();
    let mut messages = Cursor::new(&received[b"BEGIN\r\n".len()..]);
    let serials: Vec<_> = std::iter::from_fn(|| {
        let start = messages.position() as usize;
        read_message(&mut messages).ok()?;
        let bytes = &messages.get_ref()[start + 8..start + 12];
        Some(u32::from_ne_bytes(bytes.try_into().unwrap()))
    })
    .collect();
    assert_eq!(serials, [1, 2]);
}
