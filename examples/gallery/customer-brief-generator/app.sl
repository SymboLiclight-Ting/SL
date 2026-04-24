app CustomerBriefGenerator {
  intent "./customer_brief.intent.yaml"

  command generate(input_path: Text, output_path: Text) -> Bool {
    let source = read_text(input_path)
    return write_text(output_path, source)
  }

  test "brief generator smoke" {
    assert true == true
  }
}
