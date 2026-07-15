# SPDX-License-Identifier: MPL-2.0
import shutil
from abc import ABCMeta, abstractmethod
from pathlib import Path

import anyio

from pyqcrbox import logger
from pyqcrbox.data_management import DataManager
from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import (
    Cif2CifOptions,
    CifDataFileParameter,
    DeclaredOutputs,
)


class BaseCalculation(metaclass=ABCMeta):
    """Abstract base class for calculation status tracking.

    Parameters
    ----------
    calculation_id : str
        Unique identifier for the calculation.
    calc_finished_event : anyio.Event
        Event that signals when the calculation is finished.
    output_dataset_id : str | None
        The dataset id which contains output from the calculation.
    exception_raised : Exception | None
        If set, this will contain a reference to an exception that was raised
        during execution of the calculation.

    """

    def __init__(self, *, calculation_id: str, calc_finished_event: anyio.Event) -> None:
        self.calculation_id = calculation_id
        self.calc_finished_event = calc_finished_event
        self.output_dataset_id = None

        # These are for error tracking, specifically for recording the exception
        # raised in an async sub-process and if the calculation was manually
        # terminated
        self.exception_raised = None

    def __repr__(self):
        """Return a string representation of the calculation instance.

        Returns
        -------
        str
            String representation of the object.

        """
        clsname = self.__class__.__name__
        return f"<{clsname}: calculation_id={self.calculation_id}>"

    def _get_returned_output_file(self) -> "str | Path | None":
        """Return the output file produced by the calculation itself, if any.

        Subclasses override this: PythonCallable calculations return the
        callable's return value, interactive sessions the finalise command's
        return value. CLI commands produce no returned file (their outputs
        are collected from the work directory via declared output parameters).
        """
        return None

    async def save_output_to_data_manager(
        self,
        data_manager: DataManager,
        *,
        merge_options: Cif2CifOptions | None = None,
        input_cif: CifDataFileParameter | None = None,
        declared_outputs: DeclaredOutputs | None = None,
        work_dir: "str | Path | None" = None,
    ) -> str | None:
        """Save the output of the calculation to the Data File Manager.

        The primary output (the pipeline-continuing CIF) is the file returned
        by the calculation (see `_get_returned_output_file`), falling back to
        the command's declared `QCrBox.output_cif` filename resolved in the
        work directory. It is merged to the unified convention when an input
        CIF and merge options are given, and stored without an artifact kind.

        Typed output artifacts declared by the command's `QCrBox.output_*`
        artifact parameters are collected from the work directory and stored
        with their artifact kind. A missing artifact fails the calculation
        when `required_output` is set, and is skipped otherwise.

        All stored files end up in a single dataset (`output_dataset_id`).

        Parameters
        ----------
        data_manager : DataManager
            An instance of the DataFile Manager.
        merge_options : Cif2CifOptions | None
            Options which will be used to create a unified CIF.
        input_cif: CifDataFileParameter | None
            The original CIF prior to being transformed to a new CIF format.
        declared_outputs : DeclaredOutputs | None
            The declared output files of the command invocation.
        work_dir : str | Path | None
            The calculation work directory in which declared output filenames
            are resolved.

        Returns
        -------
        str | None
            The dataset ID created to store the output, or None if the
            calculation produced no output files.

        """
        work_dir = Path(work_dir) if work_dir is not None else Path(".")

        primary = self._get_returned_output_file()
        if primary is not None and not isinstance(primary, str | Path):
            exc_msg = f"The return value from the calculation must be str or pathlib.Path, not {type(primary)}"
            logger.error(f"Unable to save output of calculation {self.calculation_id}: '{exc_msg}'")
            raise ValueError(exc_msg)
        if primary:
            primary = Path(primary)
        elif declared_outputs and declared_outputs.primary_cif_filename:
            candidate = work_dir / declared_outputs.primary_cif_filename
            primary = candidate if candidate.is_file() else None

        imported_ids = []
        imported_names = set()

        if primary is not None:
            if not primary.exists() or not primary.is_file():
                exc_msg = f"The return value '{primary}' from the calculation is not a file"
                logger.error(f"Unable to save output of calculation {self.calculation_id}: '{exc_msg}'")
                raise ValueError(exc_msg)

            if input_cif and merge_options:
                logger.debug("Merging primary output to unified format")
                primary = await input_cif.to_unified_format(primary, merge_options)

            logger.debug(f"Adding primary output {primary} to DataManager")
            imported_ids.append(await data_manager.import_file(primary))
            imported_names.add(Path(primary).name)

        for artifact in declared_outputs.artifacts if declared_outputs else []:
            artifact_path = work_dir / artifact.filename
            if not artifact_path.is_file():
                if artifact.required_output:
                    exc_msg = (
                        f"The command did not produce its declared required output "
                        f"{artifact.filename!r} (kind: {artifact.kind})"
                    )
                    logger.error(f"Unable to save output of calculation {self.calculation_id}: '{exc_msg}'")
                    raise ValueError(exc_msg)
                logger.info(f"Optional output {artifact.filename!r} (kind: {artifact.kind}) was not produced; skipping")
                continue

            if artifact_path.name in imported_names:
                # Dataset files are keyed by filename; copy to a unique name
                suffix = artifact_path.suffix
                base_name = artifact_path.name[: -len(suffix)] if suffix else artifact_path.name
                counter = 2
                while f"{base_name}-{counter}{suffix}" in imported_names:
                    counter += 1
                deduped = artifact_path.with_name(f"{base_name}-{counter}{suffix}")
                shutil.copy2(artifact_path, deduped)
                artifact_path = deduped

            logger.debug(f"Adding output artifact {artifact_path} (kind: {artifact.kind}) to DataManager")
            imported_ids.append(await data_manager.import_file(artifact_path, kind=artifact.kind))
            imported_names.add(artifact_path.name)

        if not imported_ids:
            logger.info("This calculation has no output files, nothing to store in the data manager")
            return None

        self.output_dataset_id = await data_manager.create_dataset_from_data_files(imported_ids)
        logger.info(f"Created Dataset {self.output_dataset_id} containing {len(imported_ids)} output file(s)")
        return self.output_dataset_id

    @abstractmethod
    async def wait_until_finished(self) -> None:
        """Wait until the calculation is finished."""

    @property
    @abstractmethod
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """

    async def get_status_details(self) -> CalculationStatusDetails:
        """Retrieve detailed status information for the calculation.

        Returns
        -------
        CalculationStatusDetails
            Detailed status information including stdout, stderr, and extra info.

        """
        return CalculationStatusDetails(
            calculation_id=self.calculation_id,
            status=self.status,
            stdout=await self.stdout,
            stderr=await self.stderr,
            output_dataset_id=self.output_dataset_id,
            extra_info=self._get_status_details_extra_info(),
        )

    def _get_status_details_extra_info(self):
        """Get additional information for status details.

        Returns
        -------
        dict
            Extra information as a dictionary.

        """
        return {}

    @property
    @abstractmethod
    async def stdout(self) -> str | None:
        """Retrieve the standard output of the calculation.

        Returns
        -------
        str or None
            The standard output, or None if not available.

        """

    @property
    @abstractmethod
    async def stderr(self) -> str | None:
        """Retrieve the standard error of the calculation.

        Returns
        -------
        str or None
            The standard error, or None if not available.

        """

    @abstractmethod
    async def terminate(self) -> None:
        """Terminate the calculation."""
