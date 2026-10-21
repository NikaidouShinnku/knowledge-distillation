


def parse_entity_relation(output):
    index = output.find("<|COMPLETE|>")
    if index != -1:
        output = output[:index]

    entities = []
    relationships = []
    lines = output.split("##")

    for line in lines:
        if line:

            line = line.strip('\n ()')
            elements = line.split("<|>")
            if elements[0] == '"entity"':
                entity = {
                    "name": elements[1].strip('"'),
                    "type": elements[2].strip('"'),
                    "description": elements[3].strip('"')
                }
                entities.append(entity)
            elif elements[0] == '"relationship"':
                relationship = {
                    "source": elements[1].strip('"'),
                    "target": elements[2].strip('"'),
                    "description": elements[3].strip('"'),
                    "strength": int(elements[4].strip('()" '))
                }
                relationships.append(relationship)

    return entities, relationships


def generate_mermaid(entities, relationships):
    import html

    ids = {entity["name"]: f"node_{index}" for index, entity in enumerate(entities)}
    lines = ["graph TD"]
    for entity in entities:
        label = html.escape(f"{entity['type']}: {entity['name']}", quote=True)
        lines.append(f'{ids[entity["name"]]}["{label}"]')
    for relationship in relationships:
        source = ids.get(relationship["source"])
        target = ids.get(relationship["target"])
        if source is not None and target is not None:
            label = html.escape(str(relationship.get("id", "")), quote=True)
            lines.append(f'{source} --> |"{label}"| {target}')
    return "\n".join(lines) + "\n"
