"""Exact import transaction shared by gated native operations and fake import tests."""
from . import require


def import_verified(identity, other_paths, ops):
    require(identity['variant'] in {'baseline', 'candidate'}, 'IMPORT_VARIANT')
    require('bmssp_native' not in ops.registry, 'NATIVE_MODULE_ALREADY_LOADED')
    require(not any(getattr(m, '__file__', None) in other_paths for m in list(ops.registry.values()) if m is not None), 'NATIVE_ALIAS')
    module = None
    try:
        # No search path or global import: operation consumes only this exact path.
        module = ops.create(identity['path'])
        ops.registry['bmssp_native'] = module
        ops.execute(module)
        require(module.__file__ == identity['path'], 'LOADED_BINARY_PATH')
        require(ops.verify(module.__file__) == identity, 'POST_IMPORT_IDENTITY')
        dependencies = ops.dependencies(identity['dependencies'])
        require(set(dependencies) == set(identity['dependencies']), 'DEPENDENCY_IMAGE_MISSING')
        return module, dependencies
    except BaseException:
        ops.registry.pop('bmssp_native', None)
        raise
