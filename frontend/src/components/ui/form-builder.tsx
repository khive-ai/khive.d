/**
 * FormBuilder component with validation and Material-UI integration
 * Built with React Hook Form for optimal performance and UX
 */

import * as React from "react";
import {
  Alert,
  alpha,
  Box,
  Button,
  CircularProgress,
  Divider,
  Grid,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Control,
  Controller,
  FieldError,
  FieldValues,
  Path,
  SubmitHandler,
  useForm,
  ValidationRule,
} from "react-hook-form";
import { styled } from "@mui/material/styles";
import { Input } from "./input";
import { cn } from "@/utils";

export interface FormFieldBase<T = any> {
  name: string;
  label: string;
  type:
    | "text"
    | "email"
    | "password"
    | "number"
    | "textarea"
    | "select"
    | "multiselect"
    | "checkbox"
    | "radio"
    | "date"
    | "file";
  placeholder?: string;
  helperText?: string;
  required?: boolean;
  disabled?: boolean;
  hidden?: boolean;
  grid?: {
    xs?: number;
    sm?: number;
    md?: number;
    lg?: number;
    xl?: number;
  };
  validation?: {
    required?: string | boolean;
    min?: ValidationRule<string | number>;
    max?: ValidationRule<string | number>;
    minLength?: ValidationRule<number>;
    maxLength?: ValidationRule<number>;
    pattern?: ValidationRule<RegExp>;
    validate?: (value: any) => boolean | string;
  };
}

export interface TextFieldConfig extends FormFieldBase {
  type: "text" | "email" | "password" | "textarea";
  multiline?: boolean;
  rows?: number;
}

export interface NumberFieldConfig extends FormFieldBase {
  type: "number";
  min?: number;
  max?: number;
  step?: number;
}

export interface SelectFieldConfig extends FormFieldBase {
  type: "select" | "multiselect";
  options: Array<{
    label: string;
    value: string | number;
    disabled?: boolean;
  }>;
}

export interface CheckboxFieldConfig extends FormFieldBase {
  type: "checkbox";
}

export interface RadioFieldConfig extends FormFieldBase {
  type: "radio";
  options: Array<{
    label: string;
    value: string | number;
  }>;
}

export interface DateFieldConfig extends FormFieldBase {
  type: "date";
}

export interface FileFieldConfig extends FormFieldBase {
  type: "file";
  accept?: string;
  multiple?: boolean;
}

export type FormField =
  | TextFieldConfig
  | NumberFieldConfig
  | SelectFieldConfig
  | CheckboxFieldConfig
  | RadioFieldConfig
  | DateFieldConfig
  | FileFieldConfig;

export interface FormSection {
  title?: string;
  description?: string;
  fields: FormField[];
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

export interface FormBuilderProps<T extends FieldValues = FieldValues> {
  sections: FormSection[];
  onSubmit: SubmitHandler<T>;
  onError?: (errors: any) => void;
  defaultValues?: Partial<T>;
  loading?: boolean;
  disabled?: boolean;
  submitText?: string;
  resetText?: string;
  showReset?: boolean;
  className?: string;
  mode?: "onChange" | "onBlur" | "onSubmit" | "onTouched" | "all";
  validationMode?: "onChange" | "onBlur" | "onSubmit";
}

const StyledForm = styled("form")(({ theme }) => ({
  "& .MuiGrid-item": {
    display: "flex",
    flexDirection: "column",
  },
}));

const FormSection = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(4),
  "&:last-child": {
    marginBottom: 0,
  },
}));

const SectionHeader = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  paddingBottom: theme.spacing(2),
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const FieldWrapper = styled(Box)(({ theme }) => ({
  display: "flex",
  flexDirection: "column",
  gap: theme.spacing(1),
}));

interface FormFieldRendererProps<T extends FieldValues> {
  field: FormField;
  control: Control<T>;
  error?: FieldError;
  disabled?: boolean;
}

function FormFieldRenderer<T extends FieldValues>({
  field,
  control,
  error,
  disabled,
}: FormFieldRendererProps<T>) {
  const theme = useTheme();

  if (field.hidden) {
    return null;
  }

  const isDisabled = disabled || field.disabled;

  return (
    <FieldWrapper>
      <Controller
        name={field.name as Path<T>}
        control={control}
        rules={field.validation}
        render={({ field: formField }) => {
          const commonProps = {
            ...formField,
            disabled: isDisabled,
            error: !!error,
            helperText: error?.message || field.helperText,
            required: field.required,
          };

          switch (field.type) {
            case "text":
            case "email":
            case "password":
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  type={field.type}
                  placeholder={field.placeholder}
                  fullWidth
                />
              );

            case "textarea":
              const textareaField = field as TextFieldConfig;
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  placeholder={field.placeholder}
                  multiline
                  rows={textareaField.rows || 4}
                  fullWidth
                />
              );

            case "number":
              const numberField = field as NumberFieldConfig;
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  type="number"
                  placeholder={field.placeholder}
                  inputProps={{
                    min: numberField.min,
                    max: numberField.max,
                    step: numberField.step,
                  }}
                  fullWidth
                />
              );

            case "select":
              const selectField = field as SelectFieldConfig;
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  select
                  SelectProps={{
                    native: false,
                  }}
                  fullWidth
                >
                  {selectField.options.map((option) => (
                    <option
                      key={option.value}
                      value={option.value}
                      disabled={option.disabled}
                    >
                      {option.label}
                    </option>
                  ))}
                </Input>
              );

            case "checkbox":
              return (
                <Box sx={{ display: "flex", alignItems: "center", mt: 1 }}>
                  <input
                    type="checkbox"
                    {...formField}
                    disabled={isDisabled}
                    style={{
                      marginRight: theme.spacing(1),
                      width: 18,
                      height: 18,
                      accentColor: theme.palette.primary.main,
                    }}
                  />
                  <Typography
                    variant="body1"
                    component="label"
                    sx={{
                      cursor: isDisabled ? "default" : "pointer",
                      color: isDisabled ? "text.disabled" : "text.primary",
                    }}
                  >
                    {field.label}
                  </Typography>
                  {field.required && (
                    <Typography color="error" sx={{ ml: 0.5 }}>
                      *
                    </Typography>
                  )}
                </Box>
              );

            case "radio":
              const radioField = field as RadioFieldConfig;
              return (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {field.label}
                    {field.required && (
                      <Typography
                        component="span"
                        color="error"
                        sx={{ ml: 0.5 }}
                      >
                        *
                      </Typography>
                    )}
                  </Typography>
                  <Box
                    sx={{ display: "flex", flexDirection: "column", gap: 1 }}
                  >
                    {radioField.options.map((option) => (
                      <Box
                        key={option.value}
                        sx={{ display: "flex", alignItems: "center" }}
                      >
                        <input
                          type="radio"
                          {...formField}
                          value={option.value}
                          disabled={isDisabled}
                          style={{
                            marginRight: theme.spacing(1),
                            width: 18,
                            height: 18,
                            accentColor: theme.palette.primary.main,
                          }}
                        />
                        <Typography
                          variant="body2"
                          component="label"
                          sx={{
                            cursor: isDisabled ? "default" : "pointer",
                            color: isDisabled
                              ? "text.disabled"
                              : "text.primary",
                          }}
                        >
                          {option.label}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              );

            case "date":
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  type="date"
                  InputLabelProps={{
                    shrink: true,
                  }}
                  fullWidth
                />
              );

            case "file":
              const fileField = field as FileFieldConfig;
              return (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {field.label}
                    {field.required && (
                      <Typography
                        component="span"
                        color="error"
                        sx={{ ml: 0.5 }}
                      >
                        *
                      </Typography>
                    )}
                  </Typography>
                  <input
                    type="file"
                    {...formField}
                    accept={fileField.accept}
                    multiple={fileField.multiple}
                    disabled={isDisabled}
                    style={{
                      padding: theme.spacing(1),
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: theme.spacing(1),
                      backgroundColor: theme.palette.background.paper,
                      cursor: isDisabled ? "default" : "pointer",
                    }}
                  />
                </Box>
              );

            default:
              return (
                <Input
                  {...commonProps}
                  label={field.label}
                  placeholder={field.placeholder}
                  fullWidth
                />
              );
          }
        }}
      />
      {error && (
        <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
          {error.message}
        </Typography>
      )}
    </FieldWrapper>
  );
}

export function FormBuilder<T extends FieldValues = FieldValues>({
  sections,
  onSubmit,
  onError,
  defaultValues,
  loading = false,
  disabled = false,
  submitText = "Submit",
  resetText = "Reset",
  showReset = true,
  className,
  mode = "onChange",
  validationMode = "onSubmit",
}: FormBuilderProps<T>) {
  const theme = useTheme();
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isValid },
  } = useForm<T>({
    defaultValues,
    mode,
    reValidateMode: validationMode,
  });

  const isFormDisabled = disabled || loading || isSubmitting;

  const handleReset = () => {
    reset(defaultValues);
  };

  const handleFormSubmit = handleSubmit((data) => {
    onSubmit(data);
  }, onError);

  return (
    <StyledForm onSubmit={handleFormSubmit} className={cn(className)}>
      {sections.map((section, sectionIndex) => (
        <FormSection key={sectionIndex}>
          {(section.title || section.description) && (
            <SectionHeader>
              {section.title && (
                <Typography variant="h6" component="h3" gutterBottom>
                  {section.title}
                </Typography>
              )}
              {section.description && (
                <Typography variant="body2" color="text.secondary">
                  {section.description}
                </Typography>
              )}
            </SectionHeader>
          )}

          <Grid container spacing={3}>
            {section.fields.map((field, fieldIndex) => {
              const fieldError = errors[field.name as keyof typeof errors] as
                | FieldError
                | undefined;

              return (
                <Grid
                  item
                  key={fieldIndex}
                  xs={field.grid?.xs || 12}
                  sm={field.grid?.sm}
                  md={field.grid?.md}
                  lg={field.grid?.lg}
                  xl={field.grid?.xl}
                >
                  <FormFieldRenderer
                    field={field}
                    control={control}
                    error={fieldError}
                    disabled={isFormDisabled}
                  />
                </Grid>
              );
            })}
          </Grid>

          {sectionIndex < sections.length - 1 && (
            <Divider sx={{ mt: 4, mb: 2 }} />
          )}
        </FormSection>
      ))}

      <Box
        sx={{
          display: "flex",
          gap: 2,
          justifyContent: "flex-end",
          mt: 4,
          pt: 3,
          borderTop: `1px solid ${theme.palette.divider}`,
        }}
      >
        {showReset && (
          <Button
            type="button"
            variant="outlined"
            onClick={handleReset}
            disabled={isFormDisabled}
            size="large"
          >
            {resetText}
          </Button>
        )}
        <Button
          type="submit"
          variant="contained"
          disabled={isFormDisabled || !isValid}
          size="large"
          startIcon={isSubmitting && <CircularProgress size={20} />}
        >
          {isSubmitting ? "Submitting..." : submitText}
        </Button>
      </Box>
    </StyledForm>
  );
}

FormBuilder.displayName = "FormBuilder";
