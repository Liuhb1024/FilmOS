// Build-time only: use macOS Foundation/ICU to derive searchable simplified text.
// Original source snapshots remain unchanged. No runtime dependency in the app.
import Foundation
let data = FileHandle.standardInput.readDataToEndOfFile()
let input = String(data: data, encoding: .utf8)!
let output = input.applyingTransform(StringTransform("Traditional-Simplified"), reverse: false)!
FileHandle.standardOutput.write(output.data(using: .utf8)!)
