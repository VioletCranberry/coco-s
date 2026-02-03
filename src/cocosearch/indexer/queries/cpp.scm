;; @doc C++ symbol extraction: functions, classes, structs, namespaces, methods

;; Classes
(class_specifier
  name: (type_identifier) @name) @definition.class

;; Structs (with body)
(struct_specifier
  name: (type_identifier) @name
  body: (field_declaration_list)) @definition.struct

;; Namespaces
(namespace_definition
  (namespace_identifier) @name) @definition.namespace

;; Top-level functions
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function

;; Pointer functions
(function_definition
  declarator: (pointer_declarator
    declarator: (function_declarator
      declarator: (identifier) @name))) @definition.function

;; Methods (qualified names like ClassName::method)
(function_definition
  declarator: (function_declarator
    declarator: (qualified_identifier
      name: (identifier) @name))) @definition.method

;; Template classes
(template_declaration
  (class_specifier
    name: (type_identifier) @name)) @definition.class

;; Template functions
(template_declaration
  (function_definition
    declarator: (function_declarator
      declarator: (identifier) @name))) @definition.function
