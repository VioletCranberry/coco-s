;; @doc TypeScript symbol extraction: functions, classes, methods, interfaces, type aliases

;; Function declarations
(function_declaration
  (identifier) @name) @definition.function

;; Class declarations
(class_declaration
  (type_identifier) @name) @definition.class

;; Method definitions
(method_definition
  (property_identifier) @name) @definition.method

;; Arrow functions assigned to variables (const foo = () => {})
(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: (arrow_function))) @definition.function

;; Interface declarations
(interface_declaration
  (type_identifier) @name) @definition.interface

;; Type alias declarations
(type_alias_declaration
  (type_identifier) @name) @definition.interface
