import { tokenizeWithMeta, isKeyValue, parseKeyValueWithMeta, isSelector, isArrow } from "./tokenizer.js";

/**
 * A successfully parsed operation.
 */
export interface ParsedOp {
  verb: string;
  positionals: string[];
  params: Record<string, string>;
  selectors: string[];
  raw: string;
  /** Set of param keys whose values were explicitly quoted (e.g., key:"value") */
  quotedParams?: Set<string>;
}

/**
 * A parse failure.
 */
export interface ParseError {
  success: false;
  error: string;
  raw: string;
}

/**
 * Parse an operation string into a structured ParsedOp.
 *
 * First token becomes the verb. Remaining tokens are classified:
 *   @-prefixed  -> selectors
 *   key:value   -> params (unless quoted or domain override)
 *   everything else -> positionals (in order)
 *
 * @param isPositional Optional domain callback: returns true to force a token
 *   as positional (e.g. column ranges like B:G). Called before isKeyValue.
 */
export function parseOp(
  input: string,
  isPositional?: (token: string) => boolean,
): ParsedOp | ParseError {
  const raw = input.trim();
  const tokens = tokenizeWithMeta(raw);

  if (tokens.length === 0) {
    return { success: false, error: "empty operation", raw };
  }

  const verb = tokens[0].text.toLowerCase();
  const positionals: string[] = [];
  const params: Record<string, string> = {};
  const selectors: string[] = [];
  const quotedParams = new Set<string>();

  for (let i = 1; i < tokens.length; i++) {
    const meta = tokens[i];
    const token = meta.text;
    if (isSelector(token)) {
      selectors.push(token);
    } else if (meta.wasQuoted) {
      // Quoted tokens are always positional — skip key:value check
      positionals.push(token);
    } else if (isPositional && isPositional(token)) {
      // Domain extension: force as positional (e.g. column ranges)
      positionals.push(token);
    } else if (isKeyValue(token)) {
      const { key, value, wasQuoted } = parseKeyValueWithMeta(token);
      params[key] = value;
      if (wasQuoted) quotedParams.add(key);
    } else {
      positionals.push(token);
    }
  }

  return { verb, positionals, params, selectors, raw, quotedParams };
}

/**
 * Type guard: check if a parse result is an error.
 */
export function isParseError(result: ParsedOp | ParseError): result is ParseError {
  return "success" in result && result.success === false;
}
