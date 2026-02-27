  Components of a Generic FCP Server

  An FCP server for any given file type (MIDI, FFMPEG, SVG, etc.) would have the following
  four components:

  1. The Semantic Model


  This is the "brain." It's a high-level, in-memory representation of the file's content.
  It understands the file's logic, not just its bytes.


   * draw.io: The model is Shapes, Edges, Groups, and Pages.
   * MIDI: The model would be Tracks, Measures, Notes (with pitch, duration, velocity),
     Instruments, and TempoChanges. It would not be a raw stream of MIDI event numbers.
   * FFMPEG (Video): The model would be a Timeline containing VideoClips, AudioClips,
     Transitions, Effects, and TextOverlays, each with properties like start/end times and
     source file paths. It would not be a string of command-line flags.

  2. The Codebook (Model Map)


  This is the "cheat sheet" the FCP server gives the LLM so it knows what vocabulary to
  use. It's a compact summary of the available actions and terminology for that specific
  file domain.


   * draw.io Codebook:
       * Types: svc, db, api
       * Verbs: add, connect, style
   * MIDI Codebook:
       * Types: note, tempo, instrument
       * Nouns: piano, guitar, drums, C4, quarter-note
       * Verbs: add, remove, modify
   * FFMPEG Codebook:
       * Types: clip, transition, text
       * Nouns: crossfade, wipe-left, grayscale
       * Verbs: add, trim, split, overlay

  3. The Operation Language

  The LLM uses a simple, universal syntax to send instructions. The meaning of the words
  changes based on the Codebook, but the structure is always the same: VERB [TYPE] TARGET
  [key:value].


   * draw.io:
       * add svc AuthService theme:blue
   * MIDI:
       * add note C#5 on:track:Piano at:4.1 duration:eighth velocity:90
       * modify track:Drums volume:80
   * FFMPEG:
       * add clip ./cat.mp4 to:V1 at:10s
       * add transition crossfade between:cat.mp4,dog.mp4 duration:2s
       * overlay text "Funny Animals" from:10s to:15s style:title-card

  4. The Serializer / Deserializer

  This is the engine that translates between the beautiful, clean Semantic Model and the
  messy reality of the file format. This is where the FCP server's "expertise" is encoded.


   * draw.io: Translates the Shapes/Edges model into mxGraphModel XML.
   * MIDI: Translates the Tracks/Notes model into a standard .mid file's binary byte
     stream.
   * FFMPEG: Translates the Timeline model into a complex, precisely-ordered ffmpeg
     command with filters, stream maps, and correct timings.

  How It Works in Practice: A Hypothetical FFMPEG Session

  Imagine an "FCP-FFMPEG" server. The conversation would look like this:


   1. LLM opens files: session open:./vid1.mp4,./vid2.mp4
       * FCP Server loads video metadata into its Semantic Model.


   2. LLM builds the timeline: edit ops:["add clip vid1 at:0s", "add clip vid2
      at:end:vid1"]
       * FCP Server adds clips to its internal timeline model.


   3. LLM makes a creative edit: edit op:"add transition crossfade between:vid1,vid2
      duration:1.5s"
       * FCP Server adds a transition object to the model.

   4. LLM queries the state: query q:"duration"
       * FCP Server inspects its model and replies: "Total duration is 1m 32s."


   5. LLM saves the final output: session save as:./final.mp4 format:h264_1080p
       * The FCP Server's Serializer now does the hard work. It looks at the complete
         Semantic Model (clips, transitions) and constructs the final, complex `ffmpeg`
         command line to render the video. The LLM never sees or touches this command.


SPEC BELOW
====================================

  File Context Protocol (FCP) Specification

  Version: 2026-02-26-DRAFT
  Status: Proposal
  Authors: Gemini, in collaboration with user insight.

  1. Abstract


  The File Context Protocol (FCP) defines a standardized interface for Large Language
  Models (LLMs) to interact with and manipulate complex file formats through a stateful,
  semantic intermediary. The protocol enables an LLM to treat any file—binary or text—not
  as a raw string or byte stream, but as a logical, editable document.


  This is achieved via an intermediary service, the FCP Server or "Domain Brain," which
  exposes a file's content through a Semantic Model and accepts high-level commands via a
  universal Operation Language. The FCP Server is responsible for all format-specific
  serialization and deserialization, completely shielding the LLM from the complexity of
  the underlying file encoding.

  The core principle is the separation of intent from encoding. The LLM provides creative
  and logical direction; the FCP Server provides format expertise.

  2. Key Terminology


   * LLM Agent: The AI entity (e.g., Gemini) initiating requests.
   * FCP Server (Domain Brain): A tool-based server specialized for a single file format
     family (e.g., an "SVG Server," a "MIDI Server," a "Kubernetes Server"). It implements
     the FCP interface.
   * Semantic Model: The FCP Server's internal, high-level, in-memory representation of
     the file's content. This model understands the file's logical structure (e.g.,
     musical notes, Kubernetes deployments, vector shapes).
   * Serializer Bridge: The component within the FCP Server responsible for translating
     the Semantic Model to and from the raw file format.
   * Codebook: A structured, machine-readable description of a domain's capabilities and
     current state, provided by the FCP Server to the LLM Agent. It contains the Schema
     Map and Content Map.
   * Operation Language: The simple, universal VERB [TYPE] TARGET [key:value] syntax used
     by the LLM Agent to issue commands.

  3. Standard Protocol Workflow

  An interaction between an LLM Agent and an FCP Server follows a standard, stateful
  workflow.


  Step 1: Session Initialization
  The LLM Agent starts a session with an FCP Server for a specific file.

  fcp_session op:"open" file:"./path/to/document.svg"
  or
  fcp_session op:"new"


  Outcome: The FCP Server deserializes the target file into its internal Semantic Model or
  creates a new, empty model.

  Step 2: Vocabulary Acquisition
  The LLM Agent's first action in a session is to call `fcp_help` to learn the domain
  language. This is the primary entry point for vocabulary acquisition.

  fcp_help

  Outcome: The FCP Server returns the complete Codebook — all verbs, types, named values,
  selectors, and example workflows for this domain. The Codebook MUST reflect runtime
  state, including any user-defined types or extensions.

  Optionally, the LLM Agent may then call `fcp_query q:"map"` to get a summary of the
  current file's content (object counts, structure, top-level elements). This is useful
  when working with an existing file but not required when creating from scratch.


  Step 3: Detailed Inspection (Optional)
  If the LLM Agent needs more detail about a specific object identified in the
  content_map, it uses the describe query.

  fcp_query q:"describe logo"

  Outcome: The FCP Server returns a structured object detailing the properties of the
  "logo" object from its Semantic Model.


  Step 4: Iterative Editing
  Using the vocabulary from the schema_map, the LLM Agent issues one or more commands to
  modify the Semantic Model.

  fcp_edit ops:["add circle id:dot r:5 fill:red in:logo", "style background fill:#eee"]


  Outcome: The FCP Server mutates its internal Semantic Model and returns a confirmation
  for each successful operation.

  Step 5: Serialization
  Once editing is complete, the LLM Agent instructs the server to write the changes back
  to a file.

  fcp_session op:"save" as:"./path/to/document.v2.svg"


  Outcome: The FCP Server's Serializer Bridge translates its internal Semantic Model into
  the raw file format and saves it to the specified path.

  4. Standard Tooling Interface

  Every FCP-compliant server MUST implement the following four tools:


   1. `fcp_session`
       * Description: Manages the lifecycle of a file editing session.
       * Operations: new, open, save, close, checkpoint, undo, redo.


   2. `fcp_query`
       * Description: Performs read-only inspection of the current Semantic Model.
       * Operations:
           * map: Returns a summary of the current content (object counts, structure).
           * describe <object_id>: Returns detailed properties for a specific object.
           * list [@selector]: Lists objects, optionally filtered by a selector.
           * status: Returns a summary of the session (file name, unsaved changes, etc.).
           * find <query>: Searches for elements by property value.
           * history <N>: Returns the last N events from the operation log.
           * diff checkpoint:<NAME>: Returns events since the named checkpoint.
       * Implementations SHOULD support wildcard targets (e.g., `describe *`, `events *`,
         `connections *`) to avoid per-element query loops.


   3. `fcp_edit`
       * Description: Executes one or more mutating operations on the Semantic Model.
       * Input: The `ops` parameter MUST accept arrays of arbitrary length. Each string
         MUST conform to the standard Operation Language syntax.
       * Execution: Operations execute sequentially in array order.
       * Reporting: Individual results are reported per-op.
       * Failure isolation: Failed ops do not block subsequent ops (fire-and-forget within
         the batch).


   4. `fcp_help`
       * Description: Returns the complete Codebook as a reference card. MUST include all
         verbs, types, named values, selectors, and example workflow. MUST reflect runtime
         state (user-defined types/extensions). This is the primary entry point for
         vocabulary acquisition — an LLM should call this first to learn the domain
         language.

  5. Universal Operation Language

  All operations passed to fcp_edit MUST follow the VERB [TYPE] TARGET [key:value]*
  structure.

   * VERB: The action to perform (e.g., add, modify, remove).
   * TYPE: The class of object to create, as defined in the Codebook (e.g., rect,
     deployment, note). Required for verbs like add.
   * TARGET: The ID or selector of the object(s) to act on.
   * KEY:VALUE: A list of space-separated parameters that modify the operation.

  ### 5.1 Universal Verbs

  The following verbs are part of the universal FCP vocabulary. Domain servers MUST support
  at minimum `add` and `remove`, and SHOULD support all listed verbs:

   * `add` — Create a new element
   * `remove` — Delete an element (by selector)
   * `modify` — Edit element properties in-place. PREFERRED over remove+readd for property
     changes.
   * `copy` — Duplicate matched elements to a new location
   * `repeat` — RECOMMENDED. Stamp matched elements N times at successive positions with
     auto-incrementing offsets. Eliminates repetitive copy operations for patterns.

  Domain servers MAY define additional verbs beyond this universal set.

  ### 5.2 Selectors

  Selectors use `@`-prefixed references and compose via AND (intersection). Universal
  selector types:

   * `@type:T` — Filter by element type
   * `@range:S-E` — Filter by position/region range (inclusive start and end)
   * `@all` — Match all elements
   * `@recent[:N]` — Match the last N elements from the event log (default 1)

  Domain servers MAY define additional selector types (e.g., `@track:NAME`, `@pitch:P`,
  `@channel:N` for MIDI; `@layer:NAME`, `@group:NAME` for drawing).

  ### 5.3 Fuzzy Reference Resolution

  Named references (track names, shape labels, type names) MUST support fuzzy matching via
  a resolution cascade:

   1. Exact match
   2. Case-insensitive match
   3. Normalized match (ignore hyphens, underscores, spaces)
   4. Prefix match
   5. Similarity suggestion (if no match found, suggest closest candidates)

  Short-circuit at the first unambiguous match. Multiple matches at any level = error with
  candidate list.

  6. State Digest

  Every `fcp_edit` and mutating `fcp_session` response MUST append a compact digest
  summarizing current state. The digest provides key metrics at a glance, avoiding
  follow-up queries.

  Contents are domain-specific but MUST include:

   * Object counts (shapes, tracks, events, etc.)
   * At least one structural metric (connectivity, duration, coverage)

  Examples:

   * drawio: `[5s 4e 2g p:1/2]` (5 shapes, 4 edges, 2 groups, page 1 of 2)
   * MIDI: `[3t 48e tempo:120 4/4 C-major 8bars]` (3 tracks, 48 events, tempo, time sig,
     key, measures)

  The digest is informational — it does not replace detailed queries but prevents
  unnecessary round-trips.

  7. Structural Warnings (RECOMMENDED)

  After mutations, servers SHOULD detect and report domain-specific structural issues.
  Warnings use the `?` prefix to distinguish them from errors (`!`) and success (`+`).

  Format: `? warning message`

  Domain-specific examples:

   * MIDI: Empty measures on tracks that have content elsewhere
     (`? Strings: empty at measures 5-8`)
   * Drawing: Orphan shapes with no connections
     (`? AuthService: no connections`)
   * Video/Timeline: Gaps between clips (`? Track 2: gap at 00:15-00:18`)

  Warnings are advisory — they do not fail the operation. They surface issues that would
  otherwise require manual review, catching mistakes early in the composition process.