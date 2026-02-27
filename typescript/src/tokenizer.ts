/**
 * Tokenize an operation string by whitespace, respecting quoted strings.
 * "add svc \"Auth Service\" theme:blue" -> ["add", "svc", "Auth Service", "theme:blue"]
 */
export function tokenize(input: string): string[] {
  const tokens: string[] = [];
  let i = 0;
  const len = input.length;

  while (i < len) {
    // Skip whitespace
    while (i < len && input[i] === " ") i++;
    if (i >= len) break;

    if (input[i] === '"') {
      // Quoted string
      i++; // skip opening quote
      let token = "";
      while (i < len && input[i] !== '"') {
        if (input[i] === "\\" && i + 1 < len) {
          const next = input[i + 1];
          if (next === "n") {
            token += "\n";
            i += 2;
          } else {
            i++;
            token += input[i];
            i++;
          }
        } else {
          token += input[i];
          i++;
        }
      }
      if (i < len) i++; // skip closing quote
      tokens.push(token);
    } else {
      // Unquoted token — preserve embedded quotes (e.g., key:"value" → key:"value")
      let token = "";
      while (i < len && input[i] !== " ") {
        if (input[i] === '"') {
          // Embedded quoted value — preserve quotes in token for downstream detection
          token += '"';
          i++; // skip opening quote
          while (i < len && input[i] !== '"') {
            if (input[i] === "\\" && i + 1 < len) {
              const next = input[i + 1];
              if (next === "n") {
                token += "\n";
                i += 2;
              } else {
                i++;
                token += input[i];
                i++;
              }
            } else {
              token += input[i];
              i++;
            }
          }
          if (i < len) {
            token += '"';
            i++; // skip closing quote
          }
        } else {
          token += input[i];
          i++;
        }
      }
      // Convert literal \n in unquoted tokens to actual newlines
      tokens.push(token.replace(/\\n/g, "\n"));
    }
  }

  return tokens;
}

/**
 * Check if a token is a key:value pair.
 * Must contain ":" but not start with "@" (selectors) and not be an arrow.
 */
export function isKeyValue(token: string): boolean {
  if (token.startsWith("@")) return false;
  if (isArrow(token)) return false;
  const colonIdx = token.indexOf(":");
  return colonIdx > 0 && colonIdx < token.length - 1;
}

/**
 * Parse a key:value token. The value may include colons (e.g., "style:orthogonal").
 * Strips surrounding quotes from the value for backwards compatibility.
 */
export function parseKeyValue(token: string): { key: string; value: string } {
  const colonIdx = token.indexOf(":");
  let value = token.slice(colonIdx + 1);
  // Strip surrounding quotes preserved by tokenizer
  if (value.startsWith('"') && value.endsWith('"') && value.length >= 2) {
    value = value.slice(1, -1);
  }
  return {
    key: token.slice(0, colonIdx),
    value,
  };
}

/**
 * Parse a key:value token with metadata about quoting.
 * Returns the unquoted value plus a `wasQuoted` flag.
 */
export function parseKeyValueWithMeta(token: string): { key: string; value: string; wasQuoted: boolean } {
  const colonIdx = token.indexOf(":");
  let value = token.slice(colonIdx + 1);
  let wasQuoted = false;
  if (value.startsWith('"') && value.endsWith('"') && value.length >= 2) {
    value = value.slice(1, -1);
    wasQuoted = true;
  }
  return {
    key: token.slice(0, colonIdx),
    value,
    wasQuoted,
  };
}

/**
 * Check if a token is an arrow operator.
 */
export function isArrow(token: string): boolean {
  return token === "->" || token === "<->" || token === "--";
}

/**
 * Check if a token is a selector (@-prefixed).
 */
export function isSelector(token: string): boolean {
  return token.startsWith("@");
}
