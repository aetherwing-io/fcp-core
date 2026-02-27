import { tokenize, isKeyValue, parseKeyValue, isSelector, isArrow } from "./tokenizer.js";

/**
 * A successfully parsed operation.
 */
export interface ParsedOp {
  verb: string;
  positionals: string[];
  params: Record<string, string>;
  selectors: string[];
  raw: string;
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
 *   key:value   -> params
 *   everything else -> positionals (in order)
 */
export function parseOp(input: string): ParsedOp | ParseError {
  const raw = input.trim();
  const tokens = tokenize(raw);

  if (tokens.length === 0) {
    return { success: false, error: "empty operation", raw };
  }

  const verb = tokens[0].toLowerCase();
  const positionals: string[] = [];
  const params: Record<string, string> = {};
  const selectors: string[] = [];

  for (let i = 1; i < tokens.length; i++) {
    const token = tokens[i];
    if (isSelector(token)) {
      selectors.push(token);
    } else if (isKeyValue(token)) {
      const { key, value } = parseKeyValue(token);
      params[key] = value;
    } else {
      positionals.push(token);
    }
  }

  return { verb, positionals, params, selectors, raw };
}

/**
 * Type guard: check if a parse result is an error.
 */
export function isParseError(result: ParsedOp | ParseError): result is ParseError {
  return "success" in result && result.success === false;
}
