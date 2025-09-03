/**
 * Form components built with React Hook Form and Material-UI
 * Provides consistent form styling and validation across the app
 */

import * as React from "react";
import {
  Box,
  Checkbox,
  Chip,
  FormControl,
  FormControlLabel,
  FormHelperText,
  FormLabel,
  InputLabel,
  MenuItem,
  OutlinedInput,
  RadioGroup,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import { Controller, FieldError, useFormContext } from "react-hook-form";

// Styled components for consistent form styling
const FormSection = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  "&:last-child": {
    marginBottom: 0,
  },
}));

const FormRow = styled(Stack)(({ theme }) => ({
  direction: "row",
  spacing: 2,
  alignItems: "flex-start",
  [theme.breakpoints.down("sm")]: {
    flexDirection: "column",
    "& > *": {
      width: "100%",
    },
  },
}));

// Form field interfaces
export interface FormFieldProps {
  name: string;
  label?: string;
  placeholder?: string;
  helperText?: string;
  required?: boolean;
  disabled?: boolean;
  error?: FieldError | boolean;
  fullWidth?: boolean;
  size?: "small" | "medium";
}

export interface FormTextFieldProps extends FormFieldProps {
  type?: "text" | "email" | "password" | "number" | "url" | "tel";
  multiline?: boolean;
  rows?: number;
  maxRows?: number;
}

export interface FormSelectFieldProps extends FormFieldProps {
  options: Array<{ value: string | number; label: string; disabled?: boolean }>;
  multiple?: boolean;
}

export interface FormCheckboxFieldProps extends FormFieldProps {
  color?: "primary" | "secondary" | "error" | "info" | "success" | "warning";
}

export interface FormSwitchFieldProps extends FormFieldProps {
  color?: "primary" | "secondary" | "error" | "info" | "success" | "warning";
}

// Form Text Field Component
export const FormTextField: React.FC<FormTextFieldProps> = ({
  name,
  label,
  placeholder,
  helperText,
  required = false,
  disabled = false,
  fullWidth = true,
  size = "medium",
  type = "text",
  multiline = false,
  rows,
  maxRows,
}) => {
  const { control, formState: { errors } } = useFormContext();
  const error = errors[name] as FieldError;

  return (
    <Controller
      name={name}
      control={control}
      rules={{ required: required ? `${label || name} is required` : false }}
      render={({ field }) => (
        <TextField
          {...field}
          label={label}
          placeholder={placeholder}
          helperText={error?.message || helperText}
          error={!!error}
          required={required}
          disabled={disabled}
          fullWidth={fullWidth}
          size={size}
          type={type}
          multiline={multiline}
          rows={rows}
          maxRows={maxRows}
          variant="outlined"
        />
      )}
    />
  );
};

// Form Select Field Component
export const FormSelectField: React.FC<FormSelectFieldProps> = ({
  name,
  label,
  placeholder,
  helperText,
  required = false,
  disabled = false,
  fullWidth = true,
  size = "medium",
  options,
  multiple = false,
}) => {
  const { control, formState: { errors } } = useFormContext();
  const error = errors[name] as FieldError;

  return (
    <Controller
      name={name}
      control={control}
      rules={{ required: required ? `${label || name} is required` : false }}
      render={({ field }) => (
        <FormControl fullWidth={fullWidth} error={!!error} size={size}>
          {label && <InputLabel>{label}</InputLabel>}
          <Select
            {...field}
            label={label}
            placeholder={placeholder}
            disabled={disabled}
            multiple={multiple}
            input={multiple ? <OutlinedInput label={label} /> : undefined}
            renderValue={multiple
              ? (selected) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {(selected as string[]).map((value) => {
                    const option = options.find((opt) =>
                      opt.value === value
                    );
                    return (
                      <Chip
                        key={value}
                        label={option?.label || value}
                        size="small"
                      />
                    );
                  })}
                </Box>
              )
              : undefined}
          >
            {options.map((option) => (
              <MenuItem
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </MenuItem>
            ))}
          </Select>
          {(error?.message || helperText) && (
            <FormHelperText>{error?.message || helperText}</FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
};

// Form Checkbox Field Component
export const FormCheckboxField: React.FC<FormCheckboxFieldProps> = ({
  name,
  label,
  helperText,
  required = false,
  disabled = false,
  color = "primary",
}) => {
  const { control, formState: { errors } } = useFormContext();
  const error = errors[name] as FieldError;

  return (
    <Controller
      name={name}
      control={control}
      rules={{ required: required ? `${label || name} is required` : false }}
      render={({ field }) => (
        <FormControl error={!!error} component="fieldset">
          <FormControlLabel
            control={
              <Checkbox
                {...field}
                checked={field.value || false}
                disabled={disabled}
                color={color}
              />
            }
            label={label}
            required={required}
          />
          {(error?.message || helperText) && (
            <FormHelperText>{error?.message || helperText}</FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
};

// Form Switch Field Component
export const FormSwitchField: React.FC<FormSwitchFieldProps> = ({
  name,
  label,
  helperText,
  required = false,
  disabled = false,
  color = "primary",
}) => {
  const { control, formState: { errors } } = useFormContext();
  const error = errors[name] as FieldError;

  return (
    <Controller
      name={name}
      control={control}
      rules={{ required: required ? `${label || name} is required` : false }}
      render={({ field }) => (
        <FormControl error={!!error} component="fieldset">
          <FormControlLabel
            control={
              <Switch
                {...field}
                checked={field.value || false}
                disabled={disabled}
                color={color}
              />
            }
            label={label}
            required={required}
          />
          {(error?.message || helperText) && (
            <FormHelperText>{error?.message || helperText}</FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
};

// Form Radio Group Component
export interface FormRadioGroupProps extends FormFieldProps {
  options: Array<{ value: string | number; label: string; disabled?: boolean }>;
  row?: boolean;
}

export const FormRadioGroup: React.FC<FormRadioGroupProps> = ({
  name,
  label,
  helperText,
  required = false,
  disabled = false,
  options,
  row = false,
}) => {
  const { control, formState: { errors } } = useFormContext();
  const error = errors[name] as FieldError;

  return (
    <Controller
      name={name}
      control={control}
      rules={{ required: required ? `${label || name} is required` : false }}
      render={({ field }) => (
        <FormControl error={!!error} component="fieldset">
          {label && <FormLabel component="legend">{label}</FormLabel>}
          <RadioGroup {...field} row={row}>
            {options.map((option) => (
              <FormControlLabel
                key={option.value}
                value={option.value}
                control={<React.Fragment />}
                label={option.label}
                disabled={disabled || option.disabled}
              />
            ))}
          </RadioGroup>
          {(error?.message || helperText) && (
            <FormHelperText>{error?.message || helperText}</FormHelperText>
          )}
        </FormControl>
      )}
    />
  );
};

// Form Section Component for grouping fields
export interface FormSectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
}

export const FormSectionComponent: React.FC<FormSectionProps> = ({
  title,
  description,
  children,
}) => (
  <FormSection>
    {title && (
      <Typography variant="h6" component="h3" gutterBottom>
        {title}
      </Typography>
    )}
    {description && (
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {description}
      </Typography>
    )}
    {children}
  </FormSection>
);

// Form Row Component for horizontal layouts
export interface FormRowProps {
  children: React.ReactNode;
  spacing?: number;
}

export const FormRowComponent: React.FC<FormRowProps> = ({
  children,
  spacing = 2,
}) => (
  <FormRow spacing={spacing}>
    {children}
  </FormRow>
);

// Export styled components with proper names
export { FormRow, FormSection };
export const Form = {
  TextField: FormTextField,
  SelectField: FormSelectField,
  CheckboxField: FormCheckboxField,
  SwitchField: FormSwitchField,
  RadioGroup: FormRadioGroup,
  Section: FormSectionComponent,
  Row: FormRowComponent,
};
