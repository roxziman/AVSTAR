import { Field, Input as HeadlessInput, Label } from '@headlessui/react';

interface InputProps {
    label?: string | null;
    description?: string | null;
    value: string | null;
    setValue: (text: string) => void;
}
export default function Input(props: InputProps) {
    const { label = null, value, setValue, description } = props;
    return (
        <Field className="flex items-center gap-2 cursor-pointer">
            {label && <Label>{label}</Label>}
            <HeadlessInput className="border rounded-lg p-0.5 px-1.5" name="full_name" defaultValue={value ?? ""} placeholder={description ?? ""} onChange={(e) => {
                if (setValue)
                    setValue(e.target.value);
            }} />
        </Field>
    )
}