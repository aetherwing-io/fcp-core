Phased Plan for an SVG "File Context Protocol"

  Here is a conceptual roadmap for building a full-featured SVG FCP server.


  Phase 1: Build the Semantic Core

  This phase is about creating the "brain" that understands SVG logically, completely
  independent of the XML format.


   1. Define the Semantic Model: You would create TypeScript interfaces or classes that
      mirror the core objects of the SVG spec.
       * `SvgDocument`: The root object, containing metadata and a tree of child elements.
       * `Group`: A container with its own children and transform properties.
       * `Shape` Primitives: Rect, Circle, Ellipse, Line, Polyline, Polygon. Each has
         properties like x, y, width, fill, stroke, etc.
       * `Path`: A special shape with a structured list of PathSegment objects (MoveTo,
         LineTo, CubicBezier, Arc), which is much easier to manipulate than a raw SVG path
         d string.
       * `Text`: An object containing text content, position, and font properties.


   2. Implement State Management: The server would hold this Semantic Model in memory,
      allowing it to track the current state of the drawing. This enables stateful
      operations and a true conversational workflow.

  Phase 2: Create the XML Bridge (Serializer/Deserializer)

  This is the translator between the clean Semantic Model and the messy SVG file.


   1. Deserializer (`open` command):
       * Takes an .svg file as input.
       * Uses a fast XML parser to read the file into a generic tree.
       * Walks the XML tree and, for each element (e.g., <rect>, <g>), it instantiates the
         corresponding object from your Semantic Model (new Rect(), new Group()).
       * It parses attributes (width, fill, transform) and populates the properties of the
         semantic objects. It would need to smartly parse things like
         transform="rotate(45) translate(10, 20)" into a list of transform objects in the
         model.


   2. Serializer (`save` command):
       * Walks your in-memory Semantic Model tree.
       * For each object (e.g., a Path instance), it generates the correct XML tag
         (<path>).
       * It converts the structured properties back into SVG attribute strings (e.g., the
         list of PathSegment objects becomes a valid d="..." string).
       * This ensures "round-trip" editing: opening a file, making a change via FCP, and
         saving it back doesn't destroy information the FCP server might not understand
         (by preserving unknown attributes).


  Phase 3: Design the LLM Interface (Codebook & Operations)

  This is where you define the simple, powerful language the LLM will use.


   1. Design the Codebook:
       * Types: rect, circle, path, text, group.
       * Verbs: add, remove, style, group, ungroup, move, scale, rotate, modify.
       * Attributes: A curated list of common properties like fill, stroke, stroke-width,
         opacity, radius.


   2. Implement the Operation Parser: This engine translates the LLM's commands into
      actions on the Semantic Model.
       * add circle id:my_circle r:20 at:50,50 fill:red
       * style my_circle stroke:blue stroke-width:3
       * move my_circle by:10,0
       * rotate @type:rect by:45 about:center
       * A high-level path command: modify my_path add-curve to:100,200 control1:50,150

  Phase 4: Implement Full-Featured SVG Capabilities

  With the core system in place, you can progressively add support for the more advanced
  parts of the SVG spec.


   * Gradients & Patterns:
       * define gradient id:sunset type:linear colors:"0%:blue; 100%:red"
       * style my_circle fill:gradient:sunset
   * Filters:
       * define filter id:drop_shadow type:gaussian-blur std-dev:5
       * style my_circle filter:drop_shadow
   * Animations:
       * animate my_circle attribute:r from:10 to:20 duration:2s repeat:indefinite
   * Text Manipulation:
       * add text "Hello World" to:path:my_path start-offset:10%
   * Selectors:
       * style @fill:red stroke:black (style all red objects with a black stroke)

  Conclusion


  An FCP implementation for SVG would be a model use case for the protocol. It would
  transform SVG automation from a frustrating exercise in generating verbose, error-prone
  XML into a fluid, conversational, and creative process. The LLM would be empowered to
  "think" in terms of shapes, styles, and actions, while the FCP server handles all the
  tedious and complex details of the SVG specification.