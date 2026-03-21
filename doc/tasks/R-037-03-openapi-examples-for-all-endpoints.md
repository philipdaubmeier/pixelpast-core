# R-037-03 - OpenAPI Examples for All Endpoints

## Goal

Add concrete request and response examples to every public API endpoint so the
contract is directly useful for UI work, testing, and manual inspection.

## Dependencies

- `R-037-02`

## Scope

Provide examples for all current endpoint groups:

- health
- exploration bootstrap
- exploration grid
- day context
- day detail
- social graph

Examples should cover:

- at least one representative success example per endpoint
- meaningful query examples for filtered timeline and social graph reads
- important boundary or validation errors for endpoints with explicit error
  behavior, such as invalid date ranges or range-window limits

Examples should use realistic values such as:

- ISO dates
- plausible person IDs
- plausible tag paths
- plausible location filter values
- chronology-oriented payloads consistent with PixelPast concepts

## Acceptance Criteria

- every public endpoint exposes at least one success example in the OpenAPI
  contract
- endpoints with intended validation behavior expose representative error
  examples
- examples are specific enough to support frontend integration and manual API
  exploration without guessing payload shape
