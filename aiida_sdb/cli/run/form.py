# -*- coding: utf-8 -*-
"""Commands for analyzing the formulas of structures."""
# pylint: disable=redefined-builtin
from aiida import orm
from aiida.cmdline.utils import decorators
from aiida_codtools.common.formula import (
    DifferentCompositionsError,
    MissingElementsError,
    compare_cif_structure_formula,
)
from rich import print
from rich.progress import track
import typer


def add_issue_to_extras(structure, issue):
    """Add an issue to the extras of a structure."""

    if 'issues' in structure.extras:
        issues_set = set(structure.extras['issues'])
        issues_set.add(issue)
        structure.base.extras.set('issues', list(issues_set))
    else:
        structure.base.extras.set('issues', [issue, ])    


app = typer.Typer(pretty_exceptions_show_locals=False)

@app.callback()
@decorators.with_dbenv()
def form(cif_clean_group, atol: float = 0.01):
    """
    Check the chemical formula of all structures in a group.
    """

    query = orm.QueryBuilder()

    query.append(
        orm.Group, filters={'label': cif_clean_group}, tag='group',
    ).append(
        orm.WorkChainNode, filters={'attributes.exit_status': 0}, 
        with_group='group', tag='clean_wc',
        project='id'
    ).append(
        orm.CifData, with_outgoing='clean_wc', project='*'
    ).append(
        orm.StructureData, with_incoming='clean_wc', project='*'
    )
    query.limit(100)

    print('[bold blue]Info:[/] Counting number of work chains...')
    number_workchains = query.count()
    print(f'[bold blue]Info:[/] Verifying {number_workchains} `CifCleanWorkChain`s.')

    todo_list = []

    for wc_id, cif, structure in track(query.iterall(), total=number_workchains, description='Comparing formulas: '):
        try:
            compare_cif_structure_formula(cif, structure, atol)
        except DifferentCompositionsError:
            todo_list.append((structure, 'different_comp'))
        except MissingElementsError:
            todo_list.append((structure, 'missing_elements'))
        except Exception as exc:
            print(f'[bold red]Error:[/] {exc}')
            print(f'[bold red]Error:[/] Structure PK: {structure.pk} | CIF PK: {cif.pk}')

    print(f'[bold blue]Info:[/] Found {len(todo_list)} issues.')

    for structure, issue in todo_list:
        add_issue_to_extras(structure, issue)
