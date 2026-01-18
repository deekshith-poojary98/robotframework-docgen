# Test Suite for robotframework-docgen

This directory contains comprehensive tests for the robotframework-docgen package.

## Test Structure

- `test_enum_support.py` - Tests for Enum type support in keyword arguments
- `test_parser.py` - Tests for the parser module (library parsing, keyword extraction)
- `test_generator.py` - Tests for the generator module (HTML/Markdown generation)
- `test_integration.py` - Integration tests for the complete pipeline
- `conftest.py` - Shared fixtures and pytest configuration

## Running Tests

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run all tests

```bash
pytest tests/ -v
```

### Run specific test modules

```bash
# Run only Enum support tests
pytest tests/test_enum_support.py -v

# Run only parser tests
pytest tests/test_parser.py -v

# Run only generator tests
pytest tests/test_generator.py -v

# Run only integration tests
pytest tests/test_integration.py -v
```

### Run with coverage

```bash
pip install pytest-cov
pytest tests/ --cov=robotframework_docgen --cov-report=html
```

## Test Coverage

The test suite covers:

### Enum Support
- ✅ Enum type detection in parameters
- ✅ Enum member extraction (names and values)
- ✅ Default value handling for Enum parameters
- ✅ Enum rendering in HTML output
- ✅ Enum rendering in Markdown output
- ✅ Multiple Enum types in one library
- ✅ Mixed Enum and non-Enum parameters
- ✅ Edge cases (int, float, string Enum values)

### Parser Functionality
- ✅ Library parsing (class-based and module-level)
- ✅ Keyword extraction
- ✅ Parameter extraction
- ✅ Type annotation handling (Union, Optional, List, Dict)
- ✅ Return type extraction
- ✅ Docstring parsing and markdown processing
- ✅ Error handling

### Generator Functionality
- ✅ HTML generation
- ✅ Markdown generation
- ✅ Template placeholder replacement
- ✅ Metadata inclusion
- ✅ Configuration handling
- ✅ Edge cases (empty keywords, no parameters, etc.)

### Integration
- ✅ Complete pipeline (parse → generate)
- ✅ File output
- ✅ Backward compatibility
- ✅ Multiple Enum types in one library

## Writing New Tests

When adding new features:

1. Add unit tests in the appropriate test module
2. Add integration tests if the feature affects the full pipeline
3. Update this README if adding new test categories
4. Ensure tests are isolated and don't depend on external state
5. Use fixtures for common test data

## Test Fixtures

Common fixtures available:

- `enum_library_file` - Library file with Enum types
- `simple_library_file` - Simple library file
- `sample_library_info` - Sample LibraryInfo object
- `library_with_enum` - LibraryInfo with Enum parameters
