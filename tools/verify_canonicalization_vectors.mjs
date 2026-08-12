#!/usr/bin/env node
// Independent Node.js verifier for CPAS RFC 8785/JCS and digest vectors.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const JCS_PROFILE = "rfc8785-jcs-v1";
const LEGACY_PROFILE = "cpas-canonical-json-v1";
const LEGACY_DIGEST_PROFILE = "cpas-sha256-direct-v1";
const DIGEST_MAGIC = Buffer.from("CPAS-DIGEST-V2\0", "ascii");
const DEFAULT_VECTORS = resolve(
  "compliance-tests/canonicalization/cpas-canonicalization-v1.json",
);

class DuplicateKeyError extends Error {}
class NonFiniteNumberError extends Error {}
class IntegerDomainError extends Error {}
class InvalidUnicodeError extends Error {}

function assertScalarUnicode(value) {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) {
        throw new InvalidUnicodeError("unpaired high surrogate");
      }
      index += 1;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      throw new InvalidUnicodeError("unpaired low surrogate");
    }
  }
}

function canonicalize(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new NonFiniteNumberError("non-finite number");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    assertScalarUnicode(value);
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalize(item)).join(",")}]`;
  }
  if (typeof value === "object") {
    const entries = Object.keys(value)
      .sort()
      .map((key) => {
        assertScalarUnicode(key);
        return `${JSON.stringify(key)}:${canonicalize(value[key])}`;
      });
    return `{${entries.join(",")}}`;
  }
  throw new TypeError(`unsupported JSON value type: ${typeof value}`);
}

// JSON.parse discards duplicate object members. This small recursive parser
// preserves the parser-boundary guarantee required by the negative vectors.
function parseStrictJson(text) {
  let index = 0;
  const whitespace = /[\u0009\u000a\u000d\u0020]/;

  function skipWhitespace() {
    while (index < text.length && whitespace.test(text[index])) index += 1;
  }

  function parseString() {
    const start = index;
    if (text[index] !== '"') throw new SyntaxError("expected string");
    index += 1;
    while (index < text.length) {
      const character = text[index];
      if (character === "\\") {
        index += 2;
        continue;
      }
      if (character === '"') {
        index += 1;
        return JSON.parse(text.slice(start, index));
      }
      if (character.charCodeAt(0) < 0x20) {
        throw new SyntaxError("unescaped control character");
      }
      index += 1;
    }
    throw new SyntaxError("unterminated string");
  }

  function parseArray() {
    const result = [];
    index += 1;
    skipWhitespace();
    if (text[index] === "]") {
      index += 1;
      return result;
    }
    while (true) {
      result.push(parseValue());
      skipWhitespace();
      if (text[index] === "]") {
        index += 1;
        return result;
      }
      if (text[index] !== ",") throw new SyntaxError("expected array comma");
      index += 1;
      skipWhitespace();
    }
  }

  function parseObject() {
    const result = {};
    const keys = new Set();
    index += 1;
    skipWhitespace();
    if (text[index] === "}") {
      index += 1;
      return result;
    }
    while (true) {
      const key = parseString();
      if (keys.has(key)) throw new DuplicateKeyError(`duplicate key: ${key}`);
      keys.add(key);
      skipWhitespace();
      if (text[index] !== ":") throw new SyntaxError("expected object colon");
      index += 1;
      skipWhitespace();
      result[key] = parseValue();
      skipWhitespace();
      if (text[index] === "}") {
        index += 1;
        return result;
      }
      if (text[index] !== ",") throw new SyntaxError("expected object comma");
      index += 1;
      skipWhitespace();
    }
  }

  function parseValue() {
    skipWhitespace();
    if (
      text.startsWith("NaN", index) ||
      text.startsWith("Infinity", index) ||
      text.startsWith("-Infinity", index)
    ) {
      throw new NonFiniteNumberError("non-finite number token");
    }
    if (text[index] === '"') return parseString();
    if (text[index] === "[") return parseArray();
    if (text[index] === "{") return parseObject();
    for (const [token, value] of [
      ["true", true],
      ["false", false],
      ["null", null],
    ]) {
      if (text.startsWith(token, index)) {
        index += token.length;
        return value;
      }
    }
    const number = text.slice(index).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (!number) throw new SyntaxError("expected JSON value");
    index += number[0].length;
    const parsed = Number(number[0]);
    if (!/[.eE]/.test(number[0]) && !Number.isSafeInteger(parsed)) {
      throw new IntegerDomainError("integer token outside the safe JSON domain");
    }
    return parsed;
  }

  const result = parseValue();
  skipWhitespace();
  if (index !== text.length) throw new SyntaxError("trailing JSON content");
  return result;
}

function sha256(bytes) {
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

function profiledDigest(value, profile) {
  const canonical = Buffer.from(canonicalize(value), "utf8");
  const preimage = Buffer.concat([
    DIGEST_MAGIC,
    Buffer.from(profile, "ascii"),
    Buffer.from([0]),
    Buffer.from(JCS_PROFILE, "ascii"),
    Buffer.from([0]),
    canonical,
  ]);
  return sha256(preimage);
}

function classifyNegative(input) {
  try {
    canonicalize(parseStrictJson(input));
  } catch (error) {
    if (error instanceof DuplicateKeyError) return "duplicate_key";
    if (error instanceof NonFiniteNumberError) return "non_finite_number";
    if (error instanceof IntegerDomainError) return "integer_domain";
    if (error instanceof InvalidUnicodeError) return "invalid_unicode";
    return "json_parse";
  }
  return null;
}

function fail(message) {
  throw new Error(message);
}

function verify(path) {
  const vectors = parseStrictJson(readFileSync(path, "utf8"));
  if (vectors.canonicalization !== JCS_PROFILE) fail("canonicalization marker differs");
  if (vectors.digest_frame.magic_hex !== DIGEST_MAGIC.toString("hex")) {
    fail("digest frame magic differs");
  }
  let checked = 0;
  for (const vector of vectors.positive) {
    const canonical = Buffer.from(canonicalize(vector.value), "utf8");
    if (canonical.toString("hex") !== vector.canonical_hex) {
      fail(`${vector.id}: canonical bytes differ`);
    }
    if (canonical.length !== vector.canonical_length) {
      fail(`${vector.id}: canonical length differs`);
    }
    for (const [profile, expected] of Object.entries(vector.digests)) {
      if (profiledDigest(vector.value, profile) !== expected) {
        fail(`${vector.id}: digest differs for ${profile}`);
      }
      checked += 1;
    }
  }

  const legacy = vectors.legacy;
  if (legacy.canonicalization !== LEGACY_PROFILE) fail("legacy marker differs");
  if (legacy.digest_profile !== LEGACY_DIGEST_PROFILE) {
    fail("legacy digest profile differs");
  }
  const legacyBytes = Buffer.from(canonicalize(legacy.value), "utf8");
  if (legacyBytes.toString("hex") !== legacy.canonical_hex) {
    fail("legacy canonical bytes differ");
  }
  if (sha256(legacyBytes) !== legacy.digest) fail("legacy digest differs");
  checked += 1;

  for (const vector of vectors.negative) {
    const actual = classifyNegative(vector.input_json);
    if (actual !== vector.expected_error) {
      fail(`${vector.id}: expected ${vector.expected_error}, observed ${actual}`);
    }
    checked += 1;
  }
  return checked;
}

try {
  const path = resolve(process.argv[2] ?? DEFAULT_VECTORS);
  const checked = verify(path);
  console.log(`canonicalization vector verification passed: ${checked} checks (Node.js)`);
} catch (error) {
  console.error(`canonicalization vector verification failed: ${error.message}`);
  process.exitCode = 1;
}
