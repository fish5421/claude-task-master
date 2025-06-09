import fs from 'fs';
import path from 'path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const schema = JSON.parse(
	fs.readFileSync(path.resolve('schemas/tasks.schema.json'), 'utf8')
);

describe('TS-F01-U1 - tasks schema validation', () => {
	const ajv = new Ajv({ allErrors: true });
	addFormats(ajv);
	const validate = ajv.compile(schema);

	test('valid document passes', () => {
		const data = {
			version: 2,
			tasks: [
				{
					id: 1,
					title: 'Example Task',
					description: 'desc',
					status: 'pending',
					owner: null,
					impactSet: [],
					dependencies: [],
					priority: 'medium',
					details: '',
					testStrategy: '',
					subtasks: [],
					createdAt: '2024-01-01T00:00:00.000Z',
					updatedAt: '2024-01-01T00:00:00.000Z'
				}
			]
		};
		expect(validate(data)).toBe(true);
	});

	test('invalid document fails', () => {
		const data = {
			version: 2,
			tasks: [
				{
					id: 1
				}
			]
		};
		expect(validate(data)).toBe(false);
	});
});
